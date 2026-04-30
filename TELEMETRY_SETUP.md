# Cache And Telemetry Setup

The chatbot now supports:

- Redis or Google Cloud Memorystore cache for repeated answers.
- Cloud Logging for telemetry logs.
- Optional BigQuery telemetry inserts.

The app still runs locally if Redis or Google Cloud credentials are not configured.

## Local Redis

Add this to `.env`:

```env
CACHE_ENABLED=true
REDIS_URL=redis://localhost:6379/0
CACHE_TTL_SECONDS=3600
```

## Google Cloud Memorystore

Use the Memorystore Redis private IP/host:

```env
CACHE_ENABLED=true
REDIS_HOST=10.0.0.5
REDIS_PORT=6379
REDIS_DB=0
CACHE_TTL_SECONDS=3600
```

Memorystore usually works only from a VM, Cloud Run service, or GKE workload connected to the same VPC.

## Cloud Logging

Install dependencies and authenticate with Google Cloud credentials. Then add:

```env
TELEMETRY_ENABLED=true
GCP_PROJECT_ID=your-gcp-project-id
CLOUD_LOGGING_ENABLED=true
```

Each answer emits a `chat.answer` telemetry event with:

- query hash and short preview
- model choice
- duration
- selected tool
- cache hit status
- retrieved context count and sources
- response length
- error status if any

## BigQuery Telemetry

Create a table like this:

```sql
CREATE TABLE `your-gcp-project-id.analytics.chat_telemetry` (
  event_name STRING,
  event_ts TIMESTAMP,
  query_hash STRING,
  query_preview STRING,
  model_choice STRING,
  duration_ms INT64,
  status STRING,
  tool STRING,
  cache_hit BOOL,
  cache_backend STRING,
  context_count INT64,
  context_sources ARRAY<STRING>,
  response_chars INT64,
  error STRING
);
```

Then enable BigQuery inserts:

```env
TELEMETRY_ENABLED=true
GCP_PROJECT_ID=your-gcp-project-id
BIGQUERY_TELEMETRY_ENABLED=true
BIGQUERY_TELEMETRY_DATASET=analytics
BIGQUERY_TELEMETRY_TABLE=chat_telemetry
```

## Install Dependencies

```powershell
pip install -r requirements.txt
```

Then restart Streamlit:

```powershell
streamlit run ui/app.py --server.fileWatcherType none
```
