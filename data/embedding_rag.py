import hashlib
import json
import math
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False


load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INDEX_PATH = BASE_DIR / ".rag_index" / "context_vectors.json"
INDEX_VERSION = 1
GEMINI_EMBEDDING_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_EMBEDDING_MODEL = "gemini-embedding-001"
FALLBACK_EMBEDDING_MODELS = (
    "models/gemini-embedding-001",
)
_active_embedding_model: str | None = None


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in {"1", "true", "yes", "on"}


def embeddings_enabled() -> bool:
    return _env_bool("RAG_USE_EMBEDDINGS") and bool(os.getenv("GEMINI_API_KEY"))


def embedding_model() -> str:
    return os.getenv("RAG_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)


def _embedding_model_candidates() -> list[str]:
    configured = embedding_model()
    candidates = [configured, *FALLBACK_EMBEDDING_MODELS]
    unique_candidates = []
    for model in candidates:
        if model and model not in unique_candidates:
            unique_candidates.append(model)
    return unique_candidates


def _model_resource_name(model: str) -> str:
    return model if model.startswith("models/") else f"models/{model}"


def _task_type(task_type: str) -> str:
    return task_type.upper()


def _current_embedding_model() -> str:
    return _active_embedding_model or embedding_model()


def _post_json(url: str, payload: dict[str, Any], api_key: str) -> tuple[int, str]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.getcode(), response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def vector_index_path() -> Path:
    configured = os.getenv("RAG_VECTOR_INDEX_PATH")
    return Path(configured) if configured else DEFAULT_INDEX_PATH


def _document_fingerprint(documents: tuple[dict[str, str], ...]) -> str:
    payload = [
        {
            "id": item.get("id", ""),
            "title": item.get("title", ""),
            "body": item.get("body", ""),
            "source": item.get("source", ""),
        }
        for item in documents
    ]
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _embed_text(text: str, *, task_type: str) -> list[float]:
    global _active_embedding_model

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required for embeddings.")

    last_error = None
    tried_models = []
    for model in _embedding_model_candidates():
        model_name = _model_resource_name(model)
        tried_models.append(model_name)
        url = f"{GEMINI_EMBEDDING_BASE_URL}/{model_name}:embedContent"
        payload = {
            "model": model_name,
            "content": {"parts": [{"text": text[:8000]}]},
            "taskType": _task_type(task_type),
        }

        try:
            status_code, response_body = _post_json(url, payload, api_key)
            if not 200 <= status_code < 300:
                last_error = f"{status_code} {response_body}"
                continue

            result = json.loads(response_body)
            _active_embedding_model = model_name
            break
        except Exception as exc:
            last_error = exc
    else:
        raise RuntimeError(
            "No configured Gemini embedding model worked. "
            f"Tried {', '.join(tried_models)}. Last error: {last_error}"
        )

    embedding = result.get("embedding", {}).get("values") if isinstance(result, dict) else None
    if not embedding:
        raise RuntimeError("Gemini did not return an embedding.")

    return [float(value) for value in embedding]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0

    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0

    return dot / (left_norm * right_norm)


def _load_index(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write_index(path: Path, index: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")


def build_vector_index(documents: tuple[dict[str, str], ...], *, force: bool = False) -> dict[str, Any]:
    if not embeddings_enabled():
        raise RuntimeError("Set RAG_USE_EMBEDDINGS=true and GEMINI_API_KEY before building embeddings.")

    path = vector_index_path()
    fingerprint = _document_fingerprint(documents)
    model_candidates = _embedding_model_candidates()
    existing = _load_index(path)

    if (
        not force
        and existing
        and existing.get("version") == INDEX_VERSION
        and existing.get("model") in model_candidates
        and existing.get("fingerprint") == fingerprint
    ):
        return existing

    entries = []
    for item in documents:
        text = f"{item.get('title', '')}\n\n{item.get('body', '')}".strip()
        if not text:
            continue

        entries.append(
            {
                "id": item.get("id", ""),
                "title": item.get("title", ""),
                "body": item.get("body", ""),
                "source": item.get("source", ""),
                "embedding": _embed_text(text, task_type="retrieval_document"),
            }
        )

    index = {
        "version": INDEX_VERSION,
        "model": _current_embedding_model(),
        "fingerprint": fingerprint,
        "documents": entries,
    }
    _write_index(path, index)
    return index


def search_vector_context(
    query: str,
    documents: tuple[dict[str, str], ...],
    *,
    limit: int = 4,
    min_score: float = 0.35,
    allowed_sources: set[str] | frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    if not embeddings_enabled() or not query.strip() or not documents:
        return []

    try:
        index = build_vector_index(documents)
        query_embedding = _embed_text(query, task_type="retrieval_query")
    except Exception:
        return []

    scored = []
    for item in index.get("documents", []):
        if allowed_sources is not None and item.get("source", "").lower() not in allowed_sources:
            continue

        score = _cosine_similarity(query_embedding, item.get("embedding", []))
        if score >= min_score:
            scored.append((score, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)

    return [
        {
            "title": item.get("title") or "Embedded Context",
            "body": item.get("body", ""),
            "source": item.get("source") or "vector-index",
            "backend": "vector",
            "score": round(float(score), 4),
        }
        for score, item in scored[:limit]
    ]


def main() -> None:
    from data.rag import _load_documents

    index = build_vector_index(_load_documents(), force=True)
    print(json.dumps(
        {
            "index_path": str(vector_index_path()),
            "model": index.get("model"),
            "documents": len(index.get("documents", [])),
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
