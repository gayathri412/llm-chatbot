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
        self.track_top_queries = self.settings.top_query_tracking_enabled
        self.backend = "disabled"
        self._memory_cache: dict[str, str] = {}
        self._memory_query_counts: dict[str, int] = {}
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

    def make_key(
        self,
        query: str,
        model_choice: str,
        context_text: str = "",
        instruction_context: str = "",
    ) -> str:
        payload = {
            "query": query.strip(),
            "model": model_choice,
            "context": context_text.strip(),
            "instructions": instruction_context.strip(),
        }
        serialized = json.dumps(payload, sort_keys=True)
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        return f"{self.namespace}:answer:{digest}"

    def _normalize_query(self, query: str) -> str:
        return " ".join((query or "").strip().lower().split())[:500]

    def record_query(self, query: str) -> None:
        if not self.enabled or not self.track_top_queries:
            return

        normalized = self._normalize_query(query)
        if not normalized:
            return

        if self._redis_client is not None:
            try:
                self._redis_client.zincrby(f"{self.namespace}:top_queries", 1, normalized)
                return
            except Exception:
                pass

        self._memory_query_counts[normalized] = self._memory_query_counts.get(normalized, 0) + 1

    def top_queries(self, limit: int = 10) -> list[dict[str, int | str]]:
        if not self.enabled or not self.track_top_queries:
            return []

        limit = max(1, min(int(limit or 10), 100))
        if self._redis_client is not None:
            try:
                rows = self._redis_client.zrevrange(
                    f"{self.namespace}:top_queries",
                    0,
                    limit - 1,
                    withscores=True,
                )
                return [{"query": query, "count": int(score)} for query, score in rows]
            except Exception:
                pass

        ranked = sorted(
            self._memory_query_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        return [{"query": query, "count": count} for query, count in ranked[:limit]]

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
            "top_query_tracking_enabled": self.track_top_queries,
        }


answer_cache = AnswerCache()
