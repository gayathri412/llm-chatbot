# Firebase Authentication Setup

The app now uses Firebase Authentication for sign-in and account creation.

## 1. Enable Firebase Auth

1. Open the Firebase console.
2. Select your project, or create one for the same Google Cloud project.
3. Go to **Authentication**.
4. Open **Sign-in method**.
5. Enable **Email/Password**.

## 2. Get the Web API Key

In Firebase project settings, copy the **Web API Key**.

For local development, add it to `.env`:

```env
AUTH_PROVIDER=firebase
FIREBASE_WEB_API_KEY=your_firebase_web_api_key
FIREBASE_PROJECT_ID=your_firebase_project_id
```

Restart Streamlit after changing `.env`:

```powershell
streamlit run .\ui\app.py
```

## 3. First Login

After Firebase is configured, the login screen shows:

- Sign in
- Create account
- Reset password

Use **Create account** to make your user. The user is stored in Firebase Authentication, not in local `.streamlit/secrets.toml`.

## 4. Cloud Run Setup

Store the Firebase Web API key in Secret Manager:

```powershell
gcloud secrets create firebase-web-api-key --project eco-precept-466120-v0
Set-Content -Path firebase_key.txt -Value "YOUR_FIREBASE_WEB_API_KEY" -NoNewline
gcloud secrets versions add firebase-web-api-key --project eco-precept-466120-v0 --data-file firebase_key.txt
Remove-Item firebase_key.txt
```

Deploy Cloud Run with the Firebase key injected:

```powershell
gcloud run deploy snti-ai-assistant `
  --project eco-precept-466120-v0 `
  --region asia-south1 `
  --set-env-vars AUTH_PROVIDER=firebase,FIREBASE_PROJECT_ID=eco-precept-466120-v0 `
  --set-secrets FIREBASE_WEB_API_KEY=firebase-web-api-key:latest
```

Do not commit `.env`, `.streamlit/secrets.toml`, or temporary key files.
