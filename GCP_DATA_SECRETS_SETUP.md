# GCP Data Layer, Secrets, And IAM Setup

This project now supports:

- Raw JSON -> staging GCS bucket -> BigQuery curated context table.
- Secret Manager for API keys.
- Service Account + IAM permissions for BigQuery, GCS, logging, and secrets.
- BigQuery-first RAG with local JSON fallback.

## 1. Choose Project Values

Use your selected Google Cloud project ID:

```text
eco-precept-466120-v0
```

Choose a globally unique bucket name:

```text
eco-precept-466120-v0-snti-staging
```

Recommended region:

```text
asia-south1
```

## 2. Enable APIs

```powershell
gcloud services enable storage.googleapis.com --project eco-precept-466120-v0
gcloud services enable bigquery.googleapis.com --project eco-precept-466120-v0
gcloud services enable secretmanager.googleapis.com --project eco-precept-466120-v0
gcloud services enable logging.googleapis.com --project eco-precept-466120-v0
```

## 3. Create Service Account

```powershell
gcloud iam service-accounts create snti-chatbot-sa --project eco-precept-466120-v0 --display-name "SNTI Chatbot Service Account"
```

Service account email:

```text
snti-chatbot-sa@eco-precept-466120-v0.iam.gserviceaccount.com
```

## 4. Grant IAM Roles

```powershell
gcloud projects add-iam-policy-binding eco-precept-466120-v0 --member "serviceAccount:snti-chatbot-sa@eco-precept-466120-v0.iam.gserviceaccount.com" --role "roles/bigquery.jobUser"
gcloud projects add-iam-policy-binding eco-precept-466120-v0 --member "serviceAccount:snti-chatbot-sa@eco-precept-466120-v0.iam.gserviceaccount.com" --role "roles/bigquery.dataEditor"
gcloud projects add-iam-policy-binding eco-precept-466120-v0 --member "serviceAccount:snti-chatbot-sa@eco-precept-466120-v0.iam.gserviceaccount.com" --role "roles/storage.objectAdmin"
gcloud projects add-iam-policy-binding eco-precept-466120-v0 --member "serviceAccount:snti-chatbot-sa@eco-precept-466120-v0.iam.gserviceaccount.com" --role "roles/secretmanager.secretAccessor"
gcloud projects add-iam-policy-binding eco-precept-466120-v0 --member "serviceAccount:snti-chatbot-sa@eco-precept-466120-v0.iam.gserviceaccount.com" --role "roles/logging.logWriter"
```

## 5. Create Staging Bucket

```powershell
gcloud storage buckets create gs://eco-precept-466120-v0-snti-staging --project eco-precept-466120-v0 --location asia-south1
```

## 6. Create BigQuery Dataset And Curated Table

```powershell
bq --location=asia-south1 mk --dataset eco-precept-466120-v0:analytics
```

Run this SQL in BigQuery:

```sql
CREATE TABLE IF NOT EXISTS `eco-precept-466120-v0.analytics.chat_context_docs` (
  doc_id STRING NOT NULL,
  title STRING,
  body STRING NOT NULL,
  source STRING,
  tags ARRAY<STRING>,
  updated_at TIMESTAMP,
  ingestion_date DATE NOT NULL
)
PARTITION BY ingestion_date
CLUSTER BY source, title;
```

If you already created the earlier `ingested_at` table, create a replacement table or drop/recreate it:

```sql
DROP TABLE IF EXISTS `eco-precept-466120-v0.analytics.chat_context_docs`;
```

Then run the `CREATE TABLE` statement above.

Optional embeddings table for future vector RAG:

```sql
CREATE TABLE IF NOT EXISTS `eco-precept-466120-v0.analytics.chat_context_embeddings` (
  doc_id STRING NOT NULL,
  chunk_id STRING NOT NULL,
  chunk_text STRING NOT NULL,
  embedding ARRAY<FLOAT64>,
  source STRING,
  updated_at TIMESTAMP,
  ingestion_date DATE NOT NULL
)
PARTITION BY ingestion_date
CLUSTER BY doc_id, source;
```

## 7. Store API Keys In Secret Manager

Create secrets:

```powershell
gcloud secrets create groq-api-key --project eco-precept-466120-v0
gcloud secrets create gemini-api-key --project eco-precept-466120-v0
```

Add secret versions:

```powershell
Set-Content -Path groq_key.txt -Value "YOUR_GROQ_API_KEY" -NoNewline
gcloud secrets versions add groq-api-key --project eco-precept-466120-v0 --data-file groq_key.txt

Set-Content -Path gemini_key.txt -Value "YOUR_GEMINI_API_KEY" -NoNewline
gcloud secrets versions add gemini-api-key --project eco-precept-466120-v0 --data-file gemini_key.txt
```

## 8. Configure `.env`

```env
GCP_PROJECT_ID=eco-precept-466120-v0
GCP_LOCATION=asia-south1
GCS_STAGING_BUCKET=eco-precept-466120-v0-snti-staging

BIGQUERY_CONTEXT_DATASET=analytics
BIGQUERY_CONTEXT_TABLE=chat_context_docs
RAG_USE_BIGQUERY=true

SECRET_MANAGER_ENABLED=true
GROQ_API_KEY_SECRET=groq-api-key
GEMINI_API_KEY_SECRET=gemini-api-key

CLOUD_LOGGING_ENABLED=true
BIGQUERY_TELEMETRY_ENABLED=true
BIGQUERY_TELEMETRY_DATASET=analytics
BIGQUERY_TELEMETRY_TABLE=chat_telemetry
```

## 9. Authenticate Locally

For local development:

```powershell
gcloud auth application-default login
```

Or use a service account key only for local testing:

```powershell
gcloud iam service-accounts keys create snti-chatbot-sa.json --iam-account snti-chatbot-sa@eco-precept-466120-v0.iam.gserviceaccount.com --project eco-precept-466120-v0
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\Users\Gayathri\OneDrive\Desktop\llm-chatbot\snti-chatbot-sa.json"
```

Do not commit service account key files.

## 10. Ingest Local JSON To BigQuery

Install dependencies:

```powershell
pip install -r requirements.txt
```

Load `data/docs.json`:

```powershell
python -m data.cloud_pipeline data/docs.json
```

To also create the optional embeddings table:

```powershell
python -m data.cloud_pipeline data/docs.json --ensure-embeddings-table
```

The pipeline will:

1. Validate required fields: `doc_id`/`id` and `body`/`content`/`text`.
2. Deduplicate rows by `doc_id + updated_at`.
3. Normalize `data/docs.json` into JSONL rows with `ingestion_date`.
4. Upload JSONL to the staging GCS bucket.
5. Load the staged JSONL into `analytics.chat_context_docs`.

## 11. Test BigQuery RAG

Restart Streamlit:

```powershell
streamlit run ui/app.py --server.fileWatcherType none
```

Ask a question from `data/docs.json`.

If `RAG_USE_BIGQUERY=true`, the retriever checks BigQuery first. If BigQuery is unavailable or has no match, local JSON fallback still works.
