# Architecture Decisions

## LLM Provider

Decision: use **Vertex AI Gemini** as the production Gemini provider because the
project already uses GCP services such as BigQuery, Cloud Logging, Secret
Manager, and Cloud Storage.

Fallbacks:

- Use **Gemini API key** if Vertex AI is not configured.
- Use **Llama via Groq** as the cheaper/dev fallback and as the low-risk route.

OpenAI and Azure OpenAI are not selected for the current implementation path.

## JSON And BigQuery Shape

Use `data/sample_context_schema.json` as the reference input shape. The curated
BigQuery table is `analytics.chat_context_docs` with these core fields:

```text
doc_id STRING REQUIRED
title STRING
body STRING REQUIRED
source STRING
tags ARRAY<STRING>
allowed_roles ARRAY<STRING>
allowed_groups ARRAY<STRING>
sensitivity STRING
metadata JSON
updated_at TIMESTAMP
ingestion_date DATE REQUIRED
```

The runtime RAG permission layer currently filters by `source` using
`DATA_ACCESS_RULES`. The role/group metadata is retained in BigQuery for audits,
future query-level policies, and downstream governance.

## Application Architecture

Decision: use a **split FastAPI backend + Streamlit UI**.

- Streamlit remains the interactive UI.
- FastAPI is the backend path for chat, RAG, caching, telemetry, RBAC-aware
  access rules, and future API/mobile clients.
- This is preferred over Streamlit-only because RBAC, batching, token controls,
  and provider routing are easier to secure and scale behind an API boundary.
