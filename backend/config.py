"""Runtime configuration.

Everything comes from environment variables (a local `.env` file is loaded for
development). Nothing in this module — or anywhere in the repo — hard-codes
table names, column names or credentials: the Alberta well schema must be
inspected first (see scripts/discover_schema.py) and mapped through env vars.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
# .env feeds os.environ so the Databricks SDK (which reads DATABRICKS_* itself) sees it too.
load_dotenv(ROOT / ".env", override=False)

ALLOWED_RADII_KM: tuple[float, ...] = (1, 2, 5, 10, 20)
DEFAULT_RADIUS_KM = 5
MAX_WELL_LIMIT = 1000
DEFAULT_WELL_LIMIT = 500

# Identifiers are interpolated into SQL (they cannot be bound as parameters),
# so they must match this strict allowlist pattern.
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip()


def _env_float(name: str) -> float | None:
    raw = _env(name)
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _env_int(name: str, default: int, lo: int, hi: int) -> int:
    raw = _env(name)
    try:
        value = int(raw) if raw is not None else default
    except ValueError:
        value = default
    return max(lo, min(hi, value))


def _env_bool(name: str, default: bool = False) -> bool:
    raw = _env(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def quote_ident(name: str) -> str:
    """Return a backtick-quoted identifier, or raise if it isn't a plain identifier."""
    if not _IDENT.match(name):
        raise ValueError(f"Unsafe SQL identifier: {name!r}")
    return f"`{name}`"


# logical field -> env var holding the *source column name*
WELL_COLUMN_ENV = {
    "id": "WELLS_COL_ID",
    "latitude": "WELLS_COL_LATITUDE",
    "longitude": "WELLS_COL_LONGITUDE",
    "depth": "WELLS_COL_DEPTH",
    "well_yield": "WELLS_COL_YIELD",
    "static_water_level": "WELLS_COL_STATIC_WATER_LEVEL",
    "drilling_date": "WELLS_COL_DRILL_DATE",
    "status": "WELLS_COL_STATUS",
}
WELL_REQUIRED = ("id", "latitude", "longitude")

QUALITY_COLUMN_ENV = {
    "well_id": "QUALITY_COL_WELL_ID",
    "parameter": "QUALITY_COL_PARAMETER",
    "value": "QUALITY_COL_VALUE",
    "unit": "QUALITY_COL_UNIT",
    "sample_date": "QUALITY_COL_SAMPLE_DATE",
}
QUALITY_REQUIRED = ("well_id", "parameter", "value")


@dataclass(frozen=True)
class Settings:
    # --- Databricks connection (credentials are read by the Databricks SDK from env) ---
    databricks_host: str | None
    warehouse_id: str | None
    http_path: str | None
    genie_space_id: str | None
    catalog: str
    schema: str

    # --- mode ---
    demo_mode: bool

    # --- well table mapping ---
    wells_table: str | None
    well_columns: dict[str, str] = field(default_factory=dict)
    quality_table: str | None = None
    quality_columns: dict[str, str] = field(default_factory=dict)

    # --- units are source facts; they are never guessed ---
    depth_unit: str | None = None
    yield_unit: str | None = None
    static_water_level_unit: str | None = None
    low_yield_threshold: float | None = None
    quality_guidelines_file: str | None = None

    # --- tuning ---
    hist_bins: int = 10
    hist_depth_bin: float = 25.0
    hist_yield_bin: float = 5.0
    min_sample: int = 5
    pool_size: int = 4
    query_timeout_s: int = 30
    genie_timeout_s: int = 90
    cache_ttl_s: int = 300
    geocoder_url: str | None = None
    cors_origins: tuple[str, ...] = ()

    # ------------------------------------------------------------------ helpers
    @property
    def databricks_configured(self) -> bool:
        return bool(self.databricks_host and (self.warehouse_id or self.http_path))

    @property
    def resolved_http_path(self) -> str | None:
        if self.http_path:
            return self.http_path
        if self.warehouse_id:
            return f"/sql/1.0/warehouses/{self.warehouse_id}"
        return None

    @property
    def genie_configured(self) -> bool:
        return bool(self.genie_space_id and self.databricks_host)

    def missing_mapping(self) -> list[str]:
        """Env vars that must be set before live queries can run."""
        missing = [] if self.wells_table else ["WELLS_TABLE"]
        for key in WELL_REQUIRED:
            if key not in self.well_columns:
                missing.append(WELL_COLUMN_ENV[key])
        return missing

    def mapping_errors(self) -> list[str]:
        """Identifier-safety problems with the supplied mapping."""
        problems: list[str] = []
        names = [("CATALOG", self.catalog), ("SCHEMA", self.schema)]
        if self.wells_table:
            names.append(("WELLS_TABLE", self.wells_table))
        if self.quality_table:
            names.append(("QUALITY_TABLE", self.quality_table))
        names += [(WELL_COLUMN_ENV[k], v) for k, v in self.well_columns.items()]
        names += [(QUALITY_COLUMN_ENV[k], v) for k, v in self.quality_columns.items()]
        for label, value in names:
            if not _IDENT.match(value):
                problems.append(f"{label} is not a plain identifier")
        return problems

    @property
    def quality_enabled(self) -> bool:
        return bool(self.quality_table and all(k in self.quality_columns for k in QUALITY_REQUIRED))

    def table_fqn(self, table: str) -> str:
        return ".".join(quote_ident(p) for p in (self.catalog, self.schema, table))

    @property
    def wells_fqn(self) -> str:
        assert self.wells_table
        return self.table_fqn(self.wells_table)

    @property
    def quality_fqn(self) -> str:
        assert self.quality_table
        return self.table_fqn(self.quality_table)

    def wells_col(self, key: str) -> str | None:
        name = self.well_columns.get(key)
        return quote_ident(name) if name else None

    def quality_col(self, key: str) -> str | None:
        name = self.quality_columns.get(key)
        return quote_ident(name) if name else None

    def warnings(self) -> list[str]:
        out: list[str] = []
        if self.wells_table:
            if "depth" in self.well_columns and not self.depth_unit:
                out.append("WELLS_DEPTH_UNIT is not set; depth will be shown without a unit.")
            if "well_yield" in self.well_columns and not self.yield_unit:
                out.append("WELLS_YIELD_UNIT is not set; yield will be shown without a unit.")
        return out


def _columns(mapping: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, env_name in mapping.items():
        value = _env(env_name)
        if value:
            out[key] = value
    return out


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    cors = _env("CORS_ORIGINS", "") or ""
    return Settings(
        databricks_host=_env("DATABRICKS_HOST"),
        warehouse_id=_env("DATABRICKS_WAREHOUSE_ID"),
        http_path=_env("DATABRICKS_HTTP_PATH"),
        genie_space_id=_env("GENIE_SPACE_ID"),
        catalog=_env("DATABRICKS_CATALOG", "calgary_agent_hackathon") or "calgary_agent_hackathon",
        schema=_env("DATABRICKS_SCHEMA", "alberta_water_well_data") or "alberta_water_well_data",
        demo_mode=_env_bool("AQUAWISE_DEMO_MODE", False),
        wells_table=_env("WELLS_TABLE"),
        well_columns=_columns(WELL_COLUMN_ENV),
        quality_table=_env("QUALITY_TABLE"),
        quality_columns=_columns(QUALITY_COLUMN_ENV),
        depth_unit=_env("WELLS_DEPTH_UNIT"),
        yield_unit=_env("WELLS_YIELD_UNIT"),
        static_water_level_unit=_env("WELLS_STATIC_WATER_LEVEL_UNIT") or _env("WELLS_DEPTH_UNIT"),
        low_yield_threshold=_env_float("LOW_YIELD_THRESHOLD"),
        quality_guidelines_file=_env("QUALITY_GUIDELINES_FILE"),
        hist_bins=_env_int("HIST_BINS", 10, 4, 20),
        hist_depth_bin=_env_float("HIST_DEPTH_BIN") or 25.0,
        hist_yield_bin=_env_float("HIST_YIELD_BIN") or 5.0,
        min_sample=_env_int("MIN_SAMPLE_SIZE", 5, 1, 1000),
        pool_size=_env_int("DB_POOL_SIZE", 4, 1, 16),
        query_timeout_s=_env_int("QUERY_TIMEOUT_SECONDS", 30, 5, 300),
        genie_timeout_s=_env_int("GENIE_TIMEOUT_SECONDS", 90, 10, 600),
        cache_ttl_s=_env_int("CACHE_TTL_SECONDS", 300, 0, 86400),
        geocoder_url=_env("GEOCODER_URL"),
        cors_origins=tuple(o.strip() for o in cors.split(",") if o.strip()),
    )
