import hashlib
import json
import os
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False


load_dotenv()

try:
    import redis
except ImportError:
    redis = None


class AnswerCache:
    def __init__(self) -> None:
        self.enabled = os.getenv("CACHE_ENABLED", "true").lower() == "true"
        self.ttl_seconds = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
        self.namespace = os.getenv("CACHE_NAMESPACE", "snti-ai")
        self.backend = "disabled"
        self._memory_cache: dict[str, str] = {}
        self._redis_client = self._connect_redis()

    def _connect_redis(self):
        if not self.enabled:
            return None

        if redis is None:
            self.backend = "memory"
            return None

        redis_url = os.getenv("REDIS_URL")
        redis_host = os.getenv("REDIS_HOST")

        try:
            if redis_url:
                client = redis.Redis.from_url(redis_url, decode_responses=True)
            elif redis_host:
                client = redis.Redis(
                    host=redis_host,
                    port=int(os.getenv("REDIS_PORT", "6379")),
                    db=int(os.getenv("REDIS_DB", "0")),
                    password=os.getenv("REDIS_PASSWORD") or None,
                    ssl=os.getenv("REDIS_SSL", "false").lower() == "true",
                    decode_responses=True,
                )
            else:
                self.backend = "memory"
                return None

            client.ping()
            self.backend = "redis"
            return client
        except Exception:
            self.backend = "memory"
            return None

    def make_key(self, query: str, model_choice: str, context_text: str = "") -> str:
        payload = {
            "query": query.strip(),
            "model": model_choice,
            "context": context_text.strip(),
        }
        serialized = json.dumps(payload, sort_keys=True)
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        return f"{self.namespace}:answer:{digest}"

    def get(self, key: str) -> str | None:
        if not self.enabled:
            return None

        if self._redis_client is not None:
            try:
                return self._redis_client.get(key)
            except Exception:
                return None

        return self._memory_cache.get(key)

    def set(self, key: str, value: str) -> None:
        if not self.enabled or not value:
            return

        if self._redis_client is not None:
            try:
                self._redis_client.setex(key, self.ttl_seconds, value)
                return
            except Exception:
                pass

        self._memory_cache[key] = value

    def metadata(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "backend": self.backend,
            "ttl_seconds": self.ttl_seconds,
        }


answer_cache = AnswerCache()
