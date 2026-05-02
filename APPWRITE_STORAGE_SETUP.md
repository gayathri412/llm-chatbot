# Appwrite Storage Setup

The app supports Appwrite Storage as an upload backend for Streamlit file
uploads. It uses Appwrite's REST Storage API directly.

## 1. Create A Bucket

In Appwrite Console:

1. Open your project.
2. Go to **Storage**.
3. Create a bucket for chatbot uploads.
4. Copy the bucket ID.

## 2. Create An API Key

Create an Appwrite API key with Storage permissions for file creation and file
read/update/delete as needed by your deployment.

## 3. Configure `.env`

```env
APP_STORAGE_BACKEND=appwrite
APPWRITE_ENDPOINT=https://cloud.appwrite.io/v1
APPWRITE_PROJECT_ID=your_project_id
APPWRITE_API_KEY=your_server_api_key
APPWRITE_STORAGE_BUCKET_ID=your_bucket_id
APPWRITE_FILE_PERMISSIONS=
```

For public-readable files, set:

```env
APPWRITE_FILE_PERMISSIONS=read("any")
```

Leave `APPWRITE_FILE_PERMISSIONS` empty to keep access controlled by the server
API key and bucket policies.

## 4. Behavior

- Existing Streamlit uploads use the selected backend automatically.
- `APP_STORAGE_BACKEND=firebase` keeps the previous Firebase/GCS behavior.
- `APP_STORAGE_BACKEND=appwrite` uploads to Appwrite Storage.
- Files larger than 5 MB are uploaded in Appwrite-compatible chunks.

Appwrite's official Storage REST API uses:

```text
POST /v1/storage/buckets/{bucketId}/files
```

with multipart fields `fileId`, `file`, and optional `permissions[]`.
