"""Databricks SQL Warehouse access.

* Auth is resolved by the Databricks SDK `Config()` from the environment:
  - on Databricks Apps: the app's service principal (DATABRICKS_CLIENT_ID/SECRET are injected);
  - locally: DATABRICKS_TOKEN (PAT), OAuth, or a CLI profile.
  Credentials never leave the backend and are never logged.
* A small connection pool keeps warm sessions so repeat queries skip the TLS/session
  handshake, and lets independent statements for one request run in parallel.
"""
from __future__ import annotations

import logging
import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Sequence

from backend.config import Settings
from backend.errors import DatabricksUnavailable, ServiceNotConfigured
from backend.services.queries import Query

log = logging.getLogger(__name__)


def to_python(value: Any) -> Any:
    """Normalise connector values to JSON-friendly Python types."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()[:10] if isinstance(value, date) and not isinstance(value, datetime) else value.isoformat()
    return value


def make_sdk_config(settings: Settings):
    """SDK config with bounded retries: an unreachable workspace must fail in seconds, not the 5-minute default."""
    from databricks.sdk.core import Config

    return Config(retry_timeout_seconds=min(15, settings.query_timeout_s), http_timeout_seconds=15)  # auth from env


class DatabricksClient:
    def __init__(self, settings: Settings):
        self.s = settings
        self._idle: "queue.LifoQueue[Any]" = queue.LifoQueue()
        self._slots = threading.BoundedSemaphore(settings.pool_size)
        self._pool = ThreadPoolExecutor(max_workers=settings.pool_size, thread_name_prefix="dbx")
        self._cfg = None
        self._cfg_lock = threading.Lock()

    # ---------------------------------------------------------------- connections
    def _config(self):
        with self._cfg_lock:
            if self._cfg is None:
                self._cfg = make_sdk_config(self.s)  # reads DATABRICKS_* from the environment
            return self._cfg

    def _connect(self):
        if not self.s.databricks_configured:
            raise ServiceNotConfigured(
                "Databricks is not configured", ["DATABRICKS_HOST", "DATABRICKS_WAREHOUSE_ID"]
            )
        from databricks import sql

        cfg = self._config()
        host = (cfg.host or self.s.databricks_host or "").replace("https://", "").replace("http://", "").rstrip("/")
        return sql.connect(
            server_hostname=host,
            http_path=self.s.resolved_http_path,
            credentials_provider=lambda: cfg.authenticate,
            session_configuration={"STATEMENT_TIMEOUT": str(self.s.query_timeout_s)},
            _socket_timeout=self.s.query_timeout_s + 10,
            # fail fast on an unreachable/misconfigured workspace instead of retrying for minutes
            _retry_stop_after_attempts_count=3,
            _retry_stop_after_attempts_duration=min(15, self.s.query_timeout_s),
            _retry_delay_max=3,
            _user_agent_entry="aquawise-alberta",
        )

    def _acquire(self):
        try:
            return self._idle.get_nowait(), True
        except queue.Empty:
            return self._connect(), False

    @staticmethod
    def _close(conn) -> None:
        try:
            conn.close()
        except Exception:  # noqa: BLE001 - best effort
            pass

    # ---------------------------------------------------------------- queries
    def query(self, q: Query) -> list[dict[str, Any]]:
        """Run one statement with bound parameters. Returns rows as dicts."""
        from databricks.sql.exc import ServerOperationError

        self._slots.acquire()
        try:
            for attempt in (0, 1):
                try:
                    conn, reused = self._acquire()
                except ServiceNotConfigured:
                    raise
                except Exception as exc:  # noqa: BLE001
                    log.exception("Databricks connect failed")
                    raise DatabricksUnavailable(str(type(exc).__name__)) from exc
                try:
                    with conn.cursor() as cur:
                        cur.execute(q.sql, q.params or {})
                        cols = [d[0] for d in cur.description or []]
                        rows = cur.fetchall()
                    self._idle.put(conn)
                    return [{c: to_python(v) for c, v in zip(cols, row)} for row in rows]
                except ServerOperationError as exc:  # bad SQL / permissions: retrying won't help
                    self._close(conn)
                    log.error("Databricks statement failed: %s", exc)
                    raise DatabricksUnavailable("statement failed") from exc
                except Exception as exc:  # noqa: BLE001
                    self._close(conn)
                    if reused and attempt == 0:  # pooled session may have expired: retry once, fresh
                        continue
                    log.exception("Databricks query error")
                    raise DatabricksUnavailable(str(type(exc).__name__)) from exc
            raise DatabricksUnavailable("query failed")  # pragma: no cover
        finally:
            self._slots.release()

    def query_many(self, queries: Sequence[Query | None]) -> list[list[dict[str, Any]]]:
        """Run independent statements in parallel (each on its own pooled connection)."""
        futures = [self._pool.submit(self.query, q) if q is not None else None for q in queries]
        return [f.result() if f is not None else [] for f in futures]

    def ping(self) -> bool:
        return bool(self.query(Query("SELECT 1 AS ok")))
