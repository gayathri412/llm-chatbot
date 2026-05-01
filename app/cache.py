import hashlib
import json
from typing import Any

from app.config import get_settings

try:
    import redis
except ImportError:
    redis = None


class AnswerCache:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.enabled = self.settings.cache_enabled
        self.ttl_seconds = self.settings.cache_ttl_seconds
        self.namespace = self.settings.cache_namespace
        self.backend = "disabled"
        self._memory_cache: dict[str, str] = {}
        self._redis_client = self._connect_redis()

    def _connect_redis(self):
        if not self.enabled:
            return None

        if redis is None:
            self.backend = "memory"
            return None

        redis_url = self.settings.redis_url
        redis_host = self.settings.redis_host

        try:
            if redis_url:
                client = redis.Redis.from_url(redis_url, decode_responses=True)
            elif redis_host:
                client = redis.Redis(
                    host=redis_host,
                    port=self.settings.redis_port,
                    db=self.settings.redis_db,
                    password=self.settings.redis_password,
                    ssl=self.settings.redis_ssl,
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
