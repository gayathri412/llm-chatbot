# Firebase Storage Setup

The app uploads user files from Streamlit upload widgets to Firebase Storage.
Files are stored under:

```text
uploads/<firebase-user-id>/<app-area>/YYYY/MM/DD/<unique-file-name>
```

## 1. Enable Storage

1. Open Firebase Console.
2. Select your project.
3. Go to **Build > Storage**.
4. Click **Get started**.
5. Choose the same location as your app when possible.

## 2. Configure The Bucket

Copy the bucket name from Firebase Storage. It usually looks like one of these:

```text
your-project-id.appspot.com
your-project-id.firebasestorage.app
```

For local development, add it to `.env`:

```env
FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com
```

For Streamlit secrets, add it to `.streamlit/secrets.toml`:

```toml
[firebase]
storage_bucket = "your-project-id.appspot.com"
```

## 3. Give Cloud Run Permission

The Cloud Run runtime service account needs permission to write objects:

```powershell
gcloud storage buckets add-iam-policy-binding gs://your-project-id.appspot.com `
  --member "serviceAccount:snti-chatbot-runtime-sa@your-project-id.iam.gserviceaccount.com" `
  --role "roles/storage.objectAdmin"
```

If your service account or bucket name is different, replace those values.

## 4. Deploy

`cloudbuild.yaml` now sets:

```env
FIREBASE_STORAGE_BUCKET=$PROJECT_ID.appspot.com
```

If Firebase shows a `.firebasestorage.app` bucket instead, change that value in
`cloudbuild.yaml` before deploying.
