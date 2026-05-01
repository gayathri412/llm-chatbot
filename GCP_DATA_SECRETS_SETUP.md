# GCP Data Layer, Secrets, And IAM Setup

This project now supports:

- Raw JSON -> staging GCS bucket -> BigQuery curated context table.
- Secret Manager for API keys.
- Least-privilege Service Accounts + IAM permissions for BigQuery, GCS, logging, and secrets.
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
gcloud services enable identitytoolkit.googleapis.com --project eco-precept-466120-v0
```

Secret Manager can require billing to enable. If billing is not enabled, keep `SECRET_MANAGER_ENABLED=false` and use your local `.env` file for development.

## 3. Create Service Accounts

Use two service accounts so the running chatbot only has read access, while ingestion jobs get write access.

```powershell
gcloud iam service-accounts create snti-chatbot-runtime-sa --project eco-precept-466120-v0 --display-name "SNTI Chatbot Runtime"
gcloud iam service-accounts create snti-chatbot-ingest-sa --project eco-precept-466120-v0 --display-name "SNTI Chatbot Ingestion"
```

Service account emails:

```text
snti-chatbot-runtime-sa@eco-precept-466120-v0.iam.gserviceaccount.com
snti-chatbot-ingest-sa@eco-precept-466120-v0.iam.gserviceaccount.com
```

## 4. Grant IAM Roles

Runtime service account: read context, run BigQuery jobs, write logs, and read secrets.

```powershell
gcloud projects add-iam-policy-binding eco-precept-466120-v0 --member "serviceAccount:snti-chatbot-runtime-sa@eco-precept-466120-v0.iam.gserviceaccount.com" --role "roles/bigquery.jobUser"
bq add-iam-policy-binding --member "serviceAccount:snti-chatbot-runtime-sa@eco-precept-466120-v0.iam.gserviceaccount.com" --role "roles/bigquery.dataViewer" eco-precept-466120-v0:analytics
gcloud projects add-iam-policy-binding eco-precept-466120-v0 --member "serviceAccount:snti-chatbot-runtime-sa@eco-precept-466120-v0.iam.gserviceaccount.com" --role "roles/logging.logWriter"
gcloud projects add-iam-policy-binding eco-precept-466120-v0 --member "serviceAccount:snti-chatbot-runtime-sa@eco-precept-466120-v0.iam.gserviceaccount.com" --role "roles/secretmanager.secretAccessor"
```

Ingestion service account: write staged files and load curated BigQuery tables.

```powershell
gcloud projects add-iam-policy-binding eco-precept-466120-v0 --member "serviceAccount:snti-chatbot-ingest-sa@eco-precept-466120-v0.iam.gserviceaccount.com" --role "roles/bigquery.jobUser"
bq add-iam-policy-binding --member "serviceAccount:snti-chatbot-ingest-sa@eco-precept-466120-v0.iam.gserviceaccount.com" --role "roles/bigquery.dataEditor" eco-precept-466120-v0:analytics
gcloud storage buckets add-iam-policy-binding gs://eco-precept-466120-v0-snti-staging --member "serviceAccount:snti-chatbot-ingest-sa@eco-precept-466120-v0.iam.gserviceaccount.com" --role "roles/storage.objectAdmin"
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

This is the production setup. It requires Secret Manager to be enabled, and Google Cloud may require billing for that API.

Create secrets:

```powershell
gcloud secrets create groq-api-key --project eco-precept-466120-v0
gcloud secrets create gemini-api-key --project eco-precept-466120-v0
gcloud secrets create firebase-web-api-key --project eco-precept-466120-v0
```

Add secret versions:

```powershell
Set-Content -Path groq_key.txt -Value "YOUR_GROQ_API_KEY" -NoNewline
gcloud secrets versions add groq-api-key --project eco-precept-466120-v0 --data-file groq_key.txt

Set-Content -Path gemini_key.txt -Value "YOUR_GEMINI_API_KEY" -NoNewline
gcloud secrets versions add gemini-api-key --project eco-precept-466120-v0 --data-file gemini_key.txt

Set-Content -Path firebase_key.txt -Value "YOUR_FIREBASE_WEB_API_KEY" -NoNewline
gcloud secrets versions add firebase-web-api-key --project eco-precept-466120-v0 --data-file firebase_key.txt
```

Inject secrets into Cloud Run instead of writing keys in code:

```powershell
gcloud run deploy snti-ai-assistant --project eco-precept-466120-v0 --region asia-south1 --service-account snti-chatbot-runtime-sa@eco-precept-466120-v0.iam.gserviceaccount.com --set-secrets GROQ_API_KEY=groq-api-key:latest,GEMINI_API_KEY=gemini-api-key:latest --set-env-vars SECRET_MANAGER_ENABLED=false,PII_REDACTION_ENABLED=true,AUDIT_PROMPT_PREVIEW_ENABLED=false
```

For Firebase Authentication, also inject the Firebase Web API key:

```powershell
gcloud run deploy snti-ai-assistant --project eco-precept-466120-v0 --region asia-south1 --service-account snti-chatbot-runtime-sa@eco-precept-466120-v0.iam.gserviceaccount.com --set-secrets FIREBASE_WEB_API_KEY=firebase-web-api-key:latest --set-env-vars AUTH_PROVIDER=firebase,FIREBASE_PROJECT_ID=eco-precept-466120-v0
```

If your code should read Secret Manager directly at runtime, keep `SECRET_MANAGER_ENABLED=true` and grant `roles/secretmanager.secretAccessor` to the runtime service account.

## 8. Configure `.env`

```env
GCP_PROJECT_ID=eco-precept-466120-v0
GCP_LOCATION=asia-south1
GCS_STAGING_BUCKET=eco-precept-466120-v0-snti-staging

AUTH_PROVIDER=firebase
FIREBASE_WEB_API_KEY=your_firebase_web_api_key
FIREBASE_PROJECT_ID=eco-precept-466120-v0

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
PII_REDACTION_ENABLED=true
AUDIT_PROMPT_PREVIEW_ENABLED=false
```

## 9. Authenticate Locally

For local development:

```powershell
gcloud auth application-default login
```

Or use a service account key only for local testing:

```powershell
gcloud iam service-accounts keys create snti-chatbot-runtime-sa.json --iam-account snti-chatbot-runtime-sa@eco-precept-466120-v0.iam.gserviceaccount.com --project eco-precept-466120-v0
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\Users\Gayathri\OneDrive\Desktop\llm-chatbot\snti-chatbot-runtime-sa.json"
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

## 12. Security, Audit, And Optional Network Controls

The app now masks emails and phone numbers before sending prompts to the LLM when `PII_REDACTION_ENABLED=true`.

Telemetry/audit logs include:

- `user_id`
- `event_ts`
- `query_hash`
- `prompt_hash`
- `duration_ms`
- estimated input/output token counts
- cache status
- context source count
- PII redaction status

Raw prompt previews are disabled by default. Keep this setting unless you explicitly need prompt previews for debugging:

```env
AUDIT_PROMPT_PREVIEW_ENABLED=false
```

Optional Cloud Run private egress:

```powershell
gcloud run deploy snti-ai-assistant --project eco-precept-466120-v0 --region asia-south1 --vpc-connector YOUR_CONNECTOR --vpc-egress private-ranges-only
```

For private access to Google APIs from a VPC, enable Private Google Access on the subnet used by the connector.
