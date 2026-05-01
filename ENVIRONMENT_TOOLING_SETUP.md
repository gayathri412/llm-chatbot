# Environment And Tooling Setup

## Local Python

Use Python 3.10 or newer.

```powershell
python --version
python -m pip install -r requirements.txt
```

## Streamlit App

```powershell
streamlit run ui/app.py --server.fileWatcherType none
```

## Optional FastAPI Backend

The backend API is available at `api/main.py`.

Run locally:

```powershell
uvicorn api.main:app --reload --port 8000
```

Test:

```powershell
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d "{\"query\":\"What is phishing?\",\"model_choice\":\"Llama\"}"
```

## Docker

Build Streamlit image:

```powershell
docker build -t snti-ai-assistant .
```

Run Streamlit image:

```powershell
docker run --env-file .env -p 8080:8080 snti-ai-assistant
```

Build FastAPI image:

```powershell
docker build -f Dockerfile.api -t snti-ai-api .
```

## Cloud Build / Cloud Run

Cloud Build and Cloud Run usually require billing.

Enable APIs:

```powershell
gcloud services enable cloudbuild.googleapis.com run.googleapis.com artifactregistry.googleapis.com
```

Create Artifact Registry repo:

```powershell
gcloud artifacts repositories create snti-ai --repository-format=docker --location=asia-south1
```

Manual build/deploy:

```powershell
gcloud builds submit --config cloudbuild.yaml --substitutions=_REGION=asia-south1,_SERVICE=snti-ai-assistant
```

## GitHub/GitLab CI Trigger

After connecting your repo to Cloud Build, create a trigger that uses:

```text
cloudbuild.yaml
```

Recommended trigger:

```text
Branch: main
Build config: cloudbuild.yaml
Service account: snti-chatbot-runtime-sa
```

## Secrets

Billing-free local development:

```env
SECRET_MANAGER_ENABLED=false
GROQ_API_KEY=your_key
GEMINI_API_KEY=your_key
PII_REDACTION_ENABLED=true
AUDIT_PROMPT_PREVIEW_ENABLED=false
```

Google Secret Manager path is already implemented in code, but enabling Secret Manager requires billing on your GCP project.
Use `snti-chatbot-runtime-sa` for the running chatbot and `snti-chatbot-ingest-sa` for JSON -> GCS -> BigQuery ingestion jobs.
