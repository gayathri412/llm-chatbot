import json
import logging
import atexit
import threading
import time
from typing import Any

from app.config import get_settings
from app.security import estimate_tokens, hash_text

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
        self.batch_enabled = self.settings.telemetry_batch_enabled
        self.batch_size = max(1, self.settings.telemetry_batch_size)
        self.flush_interval_seconds = max(1, self.settings.telemetry_flush_interval_seconds)
        self._bq_client = None
        self._buffer: list[dict[str, Any]] = []
        self._last_flush = time.monotonic()
        self._lock = threading.Lock()
        self._setup_cloud_logging()
        atexit.register(self.flush)

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
        self._queue_bigquery(event)

    def _queue_bigquery(self, event: dict[str, Any]) -> None:
        if not self.batch_enabled:
            self._insert_bigquery([event])
            return

        should_flush = False
        with self._lock:
            self._buffer.append(event)
            elapsed = time.monotonic() - self._last_flush
            should_flush = (
                len(self._buffer) >= self.batch_size
                or elapsed >= self.flush_interval_seconds
            )

        if should_flush:
            self.flush()

    def flush(self) -> None:
        with self._lock:
            if not self._buffer:
                self._last_flush = time.monotonic()
                return

            events = list(self._buffer)
            self._buffer.clear()
            self._last_flush = time.monotonic()

        self._insert_bigquery(events)

    def _insert_bigquery(self, events: list[dict[str, Any]]) -> None:
        client = self._get_bq_client()
        if client is None:
            return

        table_id = f"{self.project_id}.{self.dataset}.{self.table}"
        try:
            errors = client.insert_rows_json(table_id, events)
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
    user_id: str = "anonymous",
    prompt_text: str = "",
    pii_redacted: bool = False,
    pii_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    context_items = context_items or []
    pii_counts = pii_counts or {"emails": 0, "phones": 0}
    settings = get_settings()
    audit_text = prompt_text or query
    input_tokens = estimate_tokens(audit_text)
    output_tokens = estimate_tokens(response)

    return {
        "user_id": user_id,
        "query_hash": hash_text(query),
        "query_preview": _preview(query),
        "prompt_hash": hash_text(audit_text),
        "prompt_preview": _preview(audit_text) if settings.audit_prompt_preview_enabled else "",
        "model_choice": model_choice,
        "duration_ms": duration_ms,
        "status": status,
        "tool": tool,
        "cache_hit": cache_hit,
        "cache_backend": cache_backend,
        "input_tokens_est": input_tokens,
        "output_tokens_est": output_tokens,
        "total_tokens_est": input_tokens + output_tokens,
        "pii_redacted": pii_redacted,
        "pii_counts": pii_counts,
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
