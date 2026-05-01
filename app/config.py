import os
from functools import lru_cache
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

try:
    from pydantic import BaseModel, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

    class BaseModel:
        def __init__(self, **data):
            for key, value in data.items():
                setattr(self, key, value)

    def Field(default=None, **kwargs):
        return default


load_dotenv()


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


class AppSettings(BaseModel):
    groq_api_key: str | None = Field(default=None)
    gemini_api_key: str | None = Field(default=None)

    gcp_project_id: str | None = Field(default=None)
    gcp_location: str = Field(default="US")

    cache_enabled: bool = Field(default=True)
    cache_ttl_seconds: int = Field(default=3600)
    cache_namespace: str = Field(default="snti-ai")
    redis_url: str | None = Field(default=None)
    redis_host: str | None = Field(default=None)
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)
    redis_password: str | None = Field(default=None)
    redis_ssl: bool = Field(default=False)

    telemetry_enabled: bool = Field(default=True)
    cloud_logging_enabled: bool = Field(default=True)
    bigquery_telemetry_enabled: bool = Field(default=False)
    telemetry_file_enabled: bool = Field(default=True)
    telemetry_file_path: str = Field(default="logs/chat_telemetry.jsonl")
    bigquery_telemetry_dataset: str = Field(default="analytics")
    bigquery_telemetry_table: str = Field(default="chat_telemetry")
    log_level: str = Field(default="INFO")

    gcs_staging_bucket: str | None = Field(default=None)
    bigquery_raw_dataset: str = Field(default="raw")
    bigquery_context_dataset: str = Field(default="analytics")
    bigquery_context_table: str = Field(default="chat_context_docs")
    rag_use_bigquery: bool = Field(default=False)

    secret_manager_enabled: bool = Field(default=False)
    groq_api_key_secret: str = Field(default="groq-api-key")
    gemini_api_key_secret: str = Field(default="gemini-api-key")
    pii_redaction_enabled: bool = Field(default=True)
    audit_prompt_preview_enabled: bool = Field(default=False)

    @classmethod
    def from_env(cls) -> "AppSettings":
        return cls(
            groq_api_key=os.getenv("GROQ_API_KEY") or None,
            gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
            gcp_project_id=os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT") or None,
            gcp_location=os.getenv("GCP_LOCATION", "US"),
            cache_enabled=_env_bool("CACHE_ENABLED", "true"),
            cache_ttl_seconds=_env_int("CACHE_TTL_SECONDS", 3600),
            cache_namespace=os.getenv("CACHE_NAMESPACE", "snti-ai"),
            redis_url=os.getenv("REDIS_URL") or None,
            redis_host=os.getenv("REDIS_HOST") or None,
            redis_port=_env_int("REDIS_PORT", 6379),
            redis_db=_env_int("REDIS_DB", 0),
            redis_password=os.getenv("REDIS_PASSWORD") or None,
            redis_ssl=_env_bool("REDIS_SSL"),
            telemetry_enabled=_env_bool("TELEMETRY_ENABLED", "true"),
            cloud_logging_enabled=_env_bool("CLOUD_LOGGING_ENABLED", "true"),
            bigquery_telemetry_enabled=_env_bool("BIGQUERY_TELEMETRY_ENABLED"),
            telemetry_file_enabled=_env_bool("TELEMETRY_FILE_ENABLED", "true"),
            telemetry_file_path=os.getenv("TELEMETRY_FILE_PATH", "logs/chat_telemetry.jsonl"),
            bigquery_telemetry_dataset=os.getenv("BIGQUERY_TELEMETRY_DATASET", "analytics"),
            bigquery_telemetry_table=os.getenv("BIGQUERY_TELEMETRY_TABLE", "chat_telemetry"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            gcs_staging_bucket=os.getenv("GCS_STAGING_BUCKET") or None,
            bigquery_raw_dataset=os.getenv("BIGQUERY_RAW_DATASET", "raw"),
            bigquery_context_dataset=os.getenv("BIGQUERY_CONTEXT_DATASET", "analytics"),
            bigquery_context_table=os.getenv("BIGQUERY_CONTEXT_TABLE", "chat_context_docs"),
            rag_use_bigquery=_env_bool("RAG_USE_BIGQUERY"),
            secret_manager_enabled=_env_bool("SECRET_MANAGER_ENABLED"),
            groq_api_key_secret=os.getenv("GROQ_API_KEY_SECRET", "groq-api-key"),
            gemini_api_key_secret=os.getenv("GEMINI_API_KEY_SECRET", "gemini-api-key"),
            pii_redaction_enabled=_env_bool("PII_REDACTION_ENABLED", "true"),
            audit_prompt_preview_enabled=_env_bool("AUDIT_PROMPT_PREVIEW_ENABLED"),
        )

    def public_dict(self) -> dict[str, Any]:
        hidden = {"groq_api_key", "gemini_api_key", "redis_password"}
        return {
            key: ("***" if key in hidden and value else value)
            for key, value in self.__dict__.items()
        }


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return AppSettings.from_env()
