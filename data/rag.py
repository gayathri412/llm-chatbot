import json
import math
import os
import re
from collections import Counter
from functools import lru_cache
from typing import Any

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    TfidfVectorizer = None
    cosine_similarity = None


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SOURCES = ("docs.json", "sample.json")
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
    "i", "in", "is", "it", "of", "on", "or", "that", "the", "this", "to",
    "what", "when", "where", "which", "who", "why", "with", "you", "your",
}


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in {"1", "true", "yes", "on"}


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip()


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return [token for token in tokens if token not in STOP_WORDS and len(token) > 1]


def _chunk_text(text: str, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    text = _clean_text(text)
    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end].strip())
        start = max(end - overlap, start + 1)

    return [chunk for chunk in chunks if chunk]


def _read_json_file(path: str) -> list[dict[str, Any]]:
    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        data = data.get("documents", data.get("items", []))

    return data if isinstance(data, list) else []


@lru_cache(maxsize=1)
def _load_documents() -> tuple[dict[str, str], ...]:
    documents = []

    for source_name in DEFAULT_SOURCES:
        source_path = os.path.join(BASE_DIR, source_name)
        for index, item in enumerate(_read_json_file(source_path), start=1):
            if not isinstance(item, dict):
                continue

            title = _clean_text(item.get("title", f"{source_name} #{index}"))
            body = _clean_text(item.get("body", item.get("content", item.get("text", ""))))

            for chunk_index, chunk in enumerate(_chunk_text(body), start=1):
                documents.append(
                    {
                        "id": str(item.get("id", f"{source_name}-{index}-{chunk_index}")),
                        "title": title,
                        "body": chunk,
                        "source": source_name,
                    }
                )

    return tuple(documents)


@lru_cache(maxsize=1)
def _build_tfidf_index():
    documents = _load_documents()
    corpus = [f"{doc['title']} {doc['body']}" for doc in documents]

    if not corpus or TfidfVectorizer is None:
        return documents, None, None

    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    matrix = vectorizer.fit_transform(corpus)
    return documents, vectorizer, matrix


def _keyword_score(query: str, document: dict[str, str]) -> float:
    query_tokens = _tokenize(query)
    if not query_tokens:
        return 0.0

    text = f"{document['title']} {document['body']}"
    doc_tokens = _tokenize(text)
    if not doc_tokens:
        return 0.0

    query_counts = Counter(query_tokens)
    doc_counts = Counter(doc_tokens)
    overlap = sum(min(query_counts[token], doc_counts[token]) for token in query_counts)
    coverage = overlap / len(query_counts)
    density = overlap / math.sqrt(len(doc_tokens))

    phrase_bonus = 0.2 if query.lower() in text.lower() else 0.0
    title_bonus = 0.15 if any(token in _tokenize(document["title"]) for token in query_counts) else 0.0
    return coverage + density + phrase_bonus + title_bonus


def retrieve_context(query: str, limit: int = 4, min_score: float = 0.03) -> list[dict[str, Any]]:
    query = _clean_text(query)
    if not query:
        return []

    documents, vectorizer, matrix = _build_tfidf_index()
    if not documents:
        return _fetch_bigquery_context(query, limit=limit)

    if vectorizer is not None and matrix is not None and cosine_similarity is not None:
        query_vector = vectorizer.transform([query])
        scores = cosine_similarity(query_vector, matrix).flatten()
    else:
        scores = [_keyword_score(query, doc) for doc in documents]

    ranked_indices = sorted(range(len(documents)), key=lambda index: scores[index], reverse=True)

    results = []
    for index in ranked_indices:
        score = float(scores[index])
        if score < min_score:
            break

        doc = documents[index]
        results.append(
            {
                "title": doc["title"],
                "body": doc["body"],
                "source": doc["source"],
                "backend": "json",
                "score": round(score, 4),
            }
        )

        if len(results) >= limit:
            break

    bq_results = _fetch_bigquery_context(query, limit=limit)
    return _dedupe_results([*bq_results, *results])[:limit]


def _fetch_bigquery_context(query: str, limit: int = 4) -> list[dict[str, Any]]:
    if not _env_bool("RAG_USE_BIGQUERY"):
        return []

    try:
        from data.bq_client import fetch_context_from_bq

        rows = fetch_context_from_bq(query, limit=limit)
    except Exception:
        return []

    results = []
    for row in rows:
        body = row.get("body")
        if not body:
            continue

        results.append(
            {
                "title": row.get("title") or "BigQuery Context",
                "body": body,
                "source": row.get("source") or "bigquery",
                "backend": "bigquery",
                "score": 1.0,
            }
        )

    return results


def _dedupe_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    unique_results = []
    for item in results:
        key = (item.get("title"), item.get("body"))
        if key in seen:
            continue
        seen.add(key)
        unique_results.append(item)
    return unique_results


def format_context(results: list[dict[str, Any]]) -> str:
    if not results:
        return ""

    passages = []
    for number, item in enumerate(results, start=1):
        passages.append(
            f"[{number}] {item['title']} ({item['source']}, score={item['score']})\n"
            f"{item['body']}"
        )

    return "\n\n".join(passages)


def fetch_context(query: str, limit: int = 4) -> list[str]:
    return [item["body"] for item in retrieve_context(query, limit=limit)]
