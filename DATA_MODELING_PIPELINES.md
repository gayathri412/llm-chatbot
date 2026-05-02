# Data Modeling And Pipelines

## JSON To BigQuery

Implemented flow:

```text
Raw JSON -> GCS staging path -> BigQuery curated table
```

Default GCS path:

```text
gs://<GCS_STAGING_BUCKET>/raw/context_docs/YYYY/MM/DD/<file>-<uuid>.jsonl
```

Curated table:

```text
<project>.analytics.chat_context_docs
```

Schema:

```text
doc_id STRING REQUIRED
title STRING
body STRING REQUIRED
tags ARRAY<STRING>
source STRING
allowed_roles ARRAY<STRING>
allowed_groups ARRAY<STRING>
sensitivity STRING
metadata JSON
updated_at TIMESTAMP
ingestion_date DATE REQUIRED
```

Partitioning:

```text
PARTITION BY ingestion_date
```

Clustering:

```text
CLUSTER BY source, title
```

## Data Quality

Implemented:

- Required-field validation for `doc_id`/`id`.
- Required-field validation for `body`/`content`/`text`.
- Deduplication by `doc_id + updated_at`.
- Tag normalization from list or comma-separated string.
- Role/group allow-list normalization from list or comma-separated string.
- Metadata preservation as a BigQuery JSON field.
- JSON normalization into newline-delimited JSON.

Reference input:

```powershell
python -m data.cloud_pipeline data/sample_context_schema.json
```

## Optional Embeddings Table

Implemented table helper:

```text
<project>.analytics.chat_context_embeddings
```

Schema:

```text
doc_id STRING REQUIRED
chunk_id STRING REQUIRED
chunk_text STRING REQUIRED
embedding ARRAY<FLOAT64>
source STRING
updated_at TIMESTAMP
ingestion_date DATE REQUIRED
```

Partitioning:

```text
PARTITION BY ingestion_date
```

Clustering:

```text
CLUSTER BY doc_id, source
```

Create it with:

```powershell
python -m data.cloud_pipeline data/docs.json --ensure-embeddings-table
```

## Local Embeddings Vector Search

Implemented semantic retrieval using Gemini embeddings plus a persistent local
vector index. This does not require Pinecone, PGVector, Vertex AI Vector Search,
or Firebase Storage.

Enable it in `.env`:

```env
GEMINI_API_KEY=your_gemini_api_key
RAG_USE_EMBEDDINGS=true
RAG_EMBEDDING_MODEL=gemini-embedding-001
RAG_VECTOR_INDEX_PATH=.rag_index/context_vectors.json
```

Build or refresh the vector index:

```powershell
python -m data.embedding_rag
```

Runtime retrieval order:

```text
BigQuery context if enabled -> Gemini vector index -> TF-IDF/keyword fallback
```

The generated `.rag_index/` folder is ignored by git because it is rebuildable.
