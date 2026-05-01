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
- JSON normalization into newline-delimited JSON.

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
