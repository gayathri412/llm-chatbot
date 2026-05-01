import hashlib
import json
import logging
import time
from typing import Any

from app.config import get_settings

try:
    from google.cloud import bigquery
except ImportError:
    bigquery = None

try:
    import google.cloud.logging as cloud_logging
except ImportError:
    cloud_logging = None


LOGGER_NAME = "snti-ai-telemetry"
logger = logging.getLogger(LOGGER_NAME)
if not logger.handlers:
    logging.basicConfig(level=get_settings().log_level)


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _preview(text: str, limit: int = 300) -> str:
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


class TelemetryClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.enabled = self.settings.telemetry_enabled
        self.project_id = self.settings.gcp_project_id
        self.cloud_logging_enabled = self.settings.cloud_logging_enabled
        self.bigquery_enabled = self.settings.bigquery_telemetry_enabled
        self.dataset = self.settings.bigquery_telemetry_dataset
        self.table = self.settings.bigquery_telemetry_table
        self._bq_client = None
        self._setup_cloud_logging()

    def _setup_cloud_logging(self) -> None:
        if not self.enabled or not self.cloud_logging_enabled:
            return
        if cloud_logging is None or not self.project_id:
            return

        try:
            client = cloud_logging.Client(project=self.project_id)
            client.setup_logging()
        except Exception as exc:
            logger.warning("Cloud Logging setup failed: %s", exc)

    def _get_bq_client(self):
        if not self.enabled or not self.bigquery_enabled:
            return None
        if bigquery is None or not self.project_id:
            return None

        if self._bq_client is None:
            try:
                self._bq_client = bigquery.Client(project=self.project_id)
            except Exception as exc:
                logger.warning("BigQuery telemetry setup failed: %s", exc)
                return None

        return self._bq_client

    def emit(self, event_name: str, payload: dict[str, Any]) -> None:
        if not self.enabled:
            return

        event = {
            "event_name": event_name,
            "event_ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            **payload,
        }

        logger.info("telemetry_event=%s", json.dumps(event, default=str))
        self._insert_bigquery(event)

    def _insert_bigquery(self, event: dict[str, Any]) -> None:
        client = self._get_bq_client()
        if client is None:
            return

        table_id = f"{self.project_id}.{self.dataset}.{self.table}"
        try:
            errors = client.insert_rows_json(table_id, [event])
            if errors:
                logger.warning("BigQuery telemetry insert failed: %s", errors)
        except Exception as exc:
            logger.warning("BigQuery telemetry insert failed: %s", exc)


telemetry_client = TelemetryClient()


def build_chat_payload(
    *,
    query: str,
    model_choice: str,
    duration_ms: int,
    status: str,
    tool: str = "none",
    cache_hit: bool = False,
    cache_backend: str = "disabled",
    context_items: list[dict[str, Any]] | None = None,
    response: str = "",
    error: str = "",
) -> dict[str, Any]:
    context_items = context_items or []
    return {
        "query_hash": _hash_text(query),
        "query_preview": _preview(query),
        "model_choice": model_choice,
        "duration_ms": duration_ms,
        "status": status,
        "tool": tool,
        "cache_hit": cache_hit,
        "cache_backend": cache_backend,
        "context_count": len(context_items),
        "context_sources": [
            f"{item.get('title', 'Untitled')}:{item.get('source', 'unknown')}"
            for item in context_items
        ],
        "response_chars": len(response or ""),
        "error": _preview(error, 500) if error else "",
    }


def log_chat_event(**kwargs: Any) -> None:
    telemetry_client.emit("chat.answer", build_chat_payload(**kwargs))
