"""Databricks Genie Conversation API (backend only).

Flow: start (or continue) a conversation -> bounded wait for completion -> read the
text/query attachments -> fetch the (truncated) query result table.

Location context is NOT implicit. Genie does not know the selected map point. If the
caller passes `context`, the coordinates and radius are written into the prompt text
explicitly, which is the only way Genie can use them.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Optional

from backend.config import Settings
from backend.errors import ServiceNotConfigured
from backend.models import GenieChatRequest, GenieChatResponse, GenieQuery, GenieTable

log = logging.getLogger(__name__)
MAX_RESULT_ROWS = 100
FRIENDLY_FAILURE = "The AI assistant couldn't complete your question. Please try rephrasing it."


def build_prompt(req: GenieChatRequest) -> str:
    if not req.context:
        return req.message
    c = req.context
    return (
        f"{req.message}\n\n"
        f"[Location context supplied by the user from the app map — use it only if the question is about "
        f"nearby wells: latitude {c.latitude:.5f}, longitude {c.longitude:.5f}, search radius {c.radius_km:g} km. "
        f"Filter wells by great-circle distance in kilometres from that point.]"
    )


class GenieService:
    def __init__(self, settings: Settings, client: Any | None = None):
        self.s = settings
        self._client = client

    def _workspace(self):
        if self._client is None:
            from databricks.sdk import WorkspaceClient

            from backend.services.databricks import make_sdk_config

            self._client = WorkspaceClient(config=make_sdk_config(self.s))  # auth from env / app service principal
        return self._client

    def ask(self, req: GenieChatRequest) -> GenieChatResponse:
        if not self.s.genie_configured:
            missing = [n for n, v in (("GENIE_SPACE_ID", self.s.genie_space_id), ("DATABRICKS_HOST", self.s.databricks_host)) if not v]
            raise ServiceNotConfigured("AI assistant not configured", missing)

        space_id, prompt = self.s.genie_space_id, build_prompt(req)
        genie = self._workspace().genie
        conv_id, msg_id = req.conversation_id, None
        try:
            wait = (
                genie.create_message(space_id=space_id, conversation_id=conv_id, content=prompt)
                if conv_id else genie.start_conversation(space_id=space_id, content=prompt)
            )
            conv_id = getattr(wait.response, "conversation_id", None) or conv_id
            msg_id = getattr(wait.response, "message_id", None)
            message = wait.result(timeout=timedelta(seconds=self.s.genie_timeout_s))  # bounded polling
        except TimeoutError:
            return GenieChatResponse(conversation_id=conv_id, message_id=msg_id, status="timeout",
                                     error="The AI assistant is taking too long. Please try again or ask a simpler question.")
        except Exception:  # noqa: BLE001 - SDK raises several types for failed/cancelled messages
            log.exception("Genie request failed")
            return self._failed_status(genie, space_id, conv_id, msg_id)
        return self._to_response(genie, space_id, conv_id, msg_id, message)

    # ------------------------------------------------------------------ helpers
    def _failed_status(self, genie, space_id, conv_id, msg_id) -> GenieChatResponse:
        status = "failed"
        if conv_id and msg_id:
            try:
                current = genie.get_message(space_id=space_id, conversation_id=conv_id, message_id=msg_id)
                if str(getattr(current.status, "value", current.status)) == "CANCELLED":
                    status = "cancelled"
            except Exception:  # noqa: BLE001
                pass
        return GenieChatResponse(conversation_id=conv_id, message_id=msg_id, status=status, error=FRIENDLY_FAILURE)  # type: ignore[arg-type]

    def _to_response(self, genie, space_id, conv_id, msg_id, message) -> GenieChatResponse:
        conv_id = getattr(message, "conversation_id", None) or conv_id
        msg_id = getattr(message, "message_id", None) or getattr(message, "id", None) or msg_id
        if getattr(message, "error", None):
            return GenieChatResponse(conversation_id=conv_id, message_id=msg_id, status="failed", error=FRIENDLY_FAILURE)

        texts: list[str] = []
        query: Optional[GenieQuery] = None
        table: Optional[GenieTable] = None
        for att in getattr(message, "attachments", None) or []:
            if getattr(att, "text", None) and att.text.content:
                texts.append(att.text.content)
            q = getattr(att, "query", None)
            if q is not None and query is None:
                query = GenieQuery(description=getattr(q, "description", None), sql=getattr(q, "query", None))
                table = self._fetch_table(genie, space_id, conv_id, msg_id, getattr(att, "attachment_id", None))
        answer = "\n\n".join(texts) or (query.description if query and query.description else None)
        if answer is None and table is not None:
            answer = "Here are the results."
        if answer is None:
            answer = "The assistant returned no answer for this question. Try rephrasing it."
        return GenieChatResponse(conversation_id=conv_id, message_id=msg_id, status="completed",
                                 answer=answer, query=query, data=table)

    @staticmethod
    def _fetch_table(genie, space_id, conv_id, msg_id, attachment_id) -> Optional[GenieTable]:
        if not (attachment_id and conv_id and msg_id):
            return None
        try:
            res = genie.get_message_attachment_query_result(
                space_id=space_id, conversation_id=conv_id, message_id=msg_id, attachment_id=attachment_id)
            stmt = res.statement_response
            cols = [c.name for c in (stmt.manifest.schema.columns or [])]
            data = (stmt.result.data_array if stmt.result else None) or []
            rows = [[None if v is None else str(v) for v in row] for row in data[:MAX_RESULT_ROWS]]
            total = getattr(stmt.manifest, "total_row_count", None) or len(data)
            return GenieTable(columns=cols, rows=rows, row_count=int(total),
                              truncated=int(total) > len(rows))
        except Exception:  # noqa: BLE001 - a missing table must not lose the text answer
            log.exception("Could not fetch Genie query result")
            return None
