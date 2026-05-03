# app.py — SNTI AI Assistant
# Firebase auth + Google/GitHub/Microsoft OAuth + auto-refresh sessions
# ─────────────────────────────────────────────────────────────────

import json
import os
import secrets as pysecrets
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests
import streamlit as st

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*a, **k): return False

load_dotenv()

# ─────────────────────────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────────────────────────

FIREBASE_AUTH_BASE_URL = "https://identitytoolkit.googleapis.com/v1"
FIREBASE_SECURE_TOKEN_URL = "https://securetoken.googleapis.com/v1/token"
ID_TOKEN_TTL = 3600          # Firebase idTokens last 1h
REFRESH_SKEW = 300           # refresh 5 min before expiry
SESSION_FILE = Path(".streamlit/session_cache.json")


# ─────────────────────────────────────────────────────────────────
#  EXCEPTIONS
# ─────────────────────────────────────────────────────────────────

class FirebaseAuthError(Exception): pass
class FirebaseConfigError(Exception): pass
class SocialAuthError(Exception): pass
class SessionExpired(Exception): pass


# ─────────────────────────────────────────────────────────────────
#  FIREBASE CORE
# ─────────────────────────────────────────────────────────────────

def _firebase_api_key() -> str | None:
    return os.getenv("FIREBASE_WEB_API_KEY")


def _friendly(code: str) -> str:
    m = {
        "EMAIL_EXISTS": "An account already exists for this email.",
        "EMAIL_NOT_FOUND": "No account was found for this email.",
        "INVALID_LOGIN_CREDENTIALS": "The email or password is incorrect.",
        "INVALID_PASSWORD": "The email or password is incorrect.",
        "MISSING_PASSWORD": "Please enter a password.",
        "USER_DISABLED": "This account has been disabled.",
        "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many attempts. Try again later.",
        "INVALID_EMAIL": "Please enter a valid email address.",
        "OPERATION_NOT_ALLOWED": "Email/password sign-in is not enabled in Firebase.",
        "CONFIGURATION_NOT_FOUND": "Firebase Authentication is not initialized.",
        "API_KEY_INVALID": "The Firebase Web API key is invalid.",
        "INVALID_API_KEY": "The Firebase Web API key is invalid.",
    }
    return m.get(code, f"Firebase error: {code or 'unknown'}")


def _firebase_request(endpoint: str, payload: dict) -> dict:
    api_key = _firebase_api_key()
    if not api_key:
        raise FirebaseConfigError("FIREBASE_WEB_API_KEY is not configured.")
    r = requests.post(
        f"{FIREBASE_AUTH_BASE_URL}/{endpoint}?key={api_key}",
        json=payload, timeout=20,
    )
    try:
        data = r.json()
    except ValueError:
        data = {}
    if r.ok:
        return data
    raise FirebaseAuthError(_friendly(data.get("error", {}).get("message", "")))


def _user_from_firebase(d: dict) -> dict:
    email = d.get("email", "")
    return {
        "provider": "firebase",
        "user_id": d.get("localId", "") or email,
        "username": email,
        "email": email,
        "name": d.get("displayName") or (email.split("@")[0] if email else "User"),
        "id_token": d.get("idToken", ""),
        "refresh_token": d.get("refreshToken", ""),
    }


def _sign_in(email: str, password: str) -> dict:
    return _user_from_firebase(_firebase_request(
        "accounts:signInWithPassword",
        {"email": email, "password": password, "returnSecureToken": True}))


def _create_account(email: str, password: str, name: str) -> dict:
    d = _firebase_request("accounts:signUp",
        {"email": email, "password": password, "returnSecureToken": True})
    if name:
        d = _firebase_request("accounts:update",
            {"idToken": d["idToken"], "displayName": name, "returnSecureToken": True})
    return _user_from_firebase(d)


def _send_password_reset(email: str) -> None:
    _firebase_request("accounts:sendOobCode",
        {"requestType": "PASSWORD_RESET", "email": email})


# ─────────────────────────────────────────────────────────────────
#  SESSION PERSISTENCE + REFRESH
# ─────────────────────────────────────────────────────────────────

def _load_persisted() -> dict:
    try:
        if SESSION_FILE.exists():
            return json.loads(SESSION_FILE.read_text())
    except Exception:
        pass
    return {}


def _save_persisted(data: dict) -> None:
    try:
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        SESSION_FILE.write_text(json.dumps(data))
    except Exception:
        pass


def _clear_persisted() -> None:
    try:
        SESSION_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def save_session(user: dict) -> None:
    expires_at = time.time() + ID_TOKEN_TTL
    st.session_state.authenticated = True
    st.session_state.auth_user_id = user["user_id"]
    st.session_state.auth_user = user["username"]
    st.session_state.auth_email = user["email"]
    st.session_state.auth_name = user["name"]
    st.session_state.auth_provider = user.get("provider", "firebase")
    st.session_state.firebase_id_token = user["id_token"]
    st.session_state.firebase_refresh_token = user["refresh_token"]
    st.session_state.firebase_expires_at = expires_at

    _save_persisted({
        "user_id": user["user_id"],
        "username": user["username"],
        "email": user["email"],
        "name": user["name"],
        "provider": user.get("provider", "firebase"),
        "refresh_token": user["refresh_token"],
        "id_token": user["id_token"],
        "expires_at": expires_at,
    })


def clear_session() -> None:
    for k in (
        "authenticated", "auth_user", "auth_user_id", "auth_email", "auth_name",
        "auth_provider", "firebase_id_token", "firebase_refresh_token",
        "firebase_expires_at",
    ):
        st.session_state.pop(k, None)
    _clear_persisted()


def _hydrate_from_disk() -> bool:
    if st.session_state.get("authenticated"):
        return True
    data = _load_persisted()
    if not data.get("refresh_token"):
        return False
    st.session_state.authenticated = True
    st.session_state.auth_user_id = data.get("user_id", "")
    st.session_state.auth_user = data.get("username", "")
    st.session_state.auth_email = data.get("email", "")
    st.session_state.auth_name = data.get("name", "")
    st.session_state.auth_provider = data.get("provider", "firebase")
    st.session_state.firebase_id_token = data.get("id_token", "")
    st.session_state.firebase_refresh_token = data["refresh_token"]
    st.session_state.firebase_expires_at = data.get("expires_at", 0)
    return True


def _refresh_id_token(refresh_token: str) -> dict:
    api_key = _firebase_api_key()
    if not api_key:
        raise SessionExpired("Firebase not configured.")
    r = requests.post(
        f"{FIREBASE_SECURE_TOKEN_URL}?key={api_key}",
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=20,
    )
    if not r.ok:
        raise SessionExpired("Session expired. Please sign in again.")
    data = r.json()
    return {
        "id_token": data["id_token"],
        "refresh_token": data["refresh_token"],
        "expires_at": time.time() + int(data.get("expires_in", ID_TOKEN_TTL)),
    }


def ensure_fresh_token() -> str | None:
    if not _hydrate_from_disk():
        return None

    expires_at = st.session_state.get("firebase_expires_at", 0)
    id_token = st.session_state.get("firebase_id_token")
    refresh_token = st.session_state.get("firebase_refresh_token")

    if not refresh_token:
        return None

    if id_token and time.time() < expires_at - REFRESH_SKEW:
        return id_token

    fresh = _refresh_id_token(refresh_token)
    st.session_state.firebase_id_token = fresh["id_token"]
    st.session_state.firebase_refresh_token = fresh["refresh_token"]
    st.session_state.firebase_expires_at = fresh["expires_at"]

    persisted = _load_persisted()
    persisted.update({
        "id_token": fresh["id_token"],
        "refresh_token": fresh["refresh_token"],
        "expires_at": fresh["expires_at"],
    })
    _save_persisted(persisted)
    return fresh["id_token"]


def get_current_user() -> dict | None:
    try:
        token = ensure_fresh_token()
    except SessionExpired:
        clear_session()
        return None
    if not token:
        return None
    return {
        "provider": st.session_state.get("auth_provider", "firebase"),
        "user_id": st.session_state.get("auth_user_id", ""),
        "username": st.session_state.get("auth_user", ""),
        "email": st.session_state.get("auth_email", ""),
        "name": st.session_state.get("auth_name", ""),
        "id_token": token,
    }


def authed_headers() -> dict:
    token = ensure_fresh_token()
    if not token:
        raise SessionExpired("Not signed in.")
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────────────────────────
#  SOCIAL OAUTH (Google / GitHub / Microsoft)
# ─────────────────────────────────────────────────────────────────

PROVIDERS = {
    "google": {
        "name": "Google",
        "firebase_provider_id": "google.com",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scope": "openid email profile",
        "extra_auth_params": {"prompt": "select_account", "access_type": "online"},
        "credential_field": "id_token",
    },
    "github": {
        "name": "GitHub",
        "firebase_provider_id": "github.com",
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "scope": "read:user user:email",
        "extra_auth_params": {"allow_signup": "true"},
        "credential_field": "access_token",
    },
    "microsoft": {
        "name": "Microsoft",
        "firebase_provider_id": "microsoft.com",
        "authorize_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "scope": "openid email profile User.Read",
        "extra_auth_params": {"response_mode": "query"},
        "credential_field": "id_token",
    },
}


def _env(provider: str, key: str) -> str | None:
    return os.getenv(f"{provider.upper()}_{key.upper()}")


def _redirect_uri() -> str:
    return (
        os.getenv("OAUTH_REDIRECT_URI")
        or os.getenv("APP_BASE_URL")
        or "http://localhost:8501"
    ).rstrip("/")


def _provider_ready(provider: str) -> bool:
    return bool(_env(provider, "client_id") and _env(provider, "client_secret"))


def _build_authorize_url(provider: str) -> str:
    cfg = PROVIDERS[provider]
    state = f"{provider}:{pysecrets.token_urlsafe(24)}"
    states = st.session_state.setdefault("oauth_states", {})
    states[state] = provider
    if len(states) > 20:
        for old in list(states)[:-20]:
            states.pop(old, None)

    params = {
        "client_id": _env(provider, "client_id"),
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": cfg["scope"],
        "state": state,
        **cfg.get("extra_auth_params", {}),
    }
    return f"{cfg['authorize_url']}?{urlencode(params)}"


def _exchange_code(provider: str, code: str) -> dict:
    cfg = PROVIDERS[provider]
    resp = requests.post(
        cfg["token_url"],
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": _redirect_uri(),
            "client_id": _env(provider, "client_id"),
            "client_secret": _env(provider, "client_secret"),
        },
        headers={"Accept": "application/json"},
        timeout=20,
    )
    try:
        data = resp.json()
    except ValueError:
        data = {}
    if not resp.ok:
        msg = data.get("error_description") or data.get("error") or resp.text
        raise SocialAuthError(f"{cfg['name']} token exchange failed: {msg}")
    return data


def _signin_with_firebase(provider: str, token_data: dict) -> dict:
    cfg = PROVIDERS[provider]
    field = cfg["credential_field"]
    value = token_data.get(field) or token_data.get("access_token")
    if not value:
        raise SocialAuthError(f"{cfg['name']} did not return a usable token.")
    post_body = urlencode({
        field if token_data.get(field) else "access_token": value,
        "providerId": cfg["firebase_provider_id"],
    })
    fb_data = _firebase_request(
        "accounts:signInWithIdp",
        {
            "postBody": post_body,
            "requestUri": _redirect_uri(),
            "returnIdpCredential": True,
            "returnSecureToken": True,
        },
    )
    user = _user_from_firebase(fb_data)
    user["provider"] = cfg["firebase_provider_id"]
    return user


def handle_oauth_callback() -> None:
    qp = st.query_params
    code = qp.get("code")
    state = qp.get("state")
    error = qp.get("error")

    if error:
        st.query_params.clear()
        st.error(f"Sign-in failed: {qp.get('error_description') or error}")
        return

    if not (code and state):
        return

    states = st.session_state.get("oauth_states", {})
    provider = states.pop(state, None)
    if not provider:
        return

    try:
        token_data = _exchange_code(provider, code)
        user = _signin_with_firebase(provider, token_data)
    except (SocialAuthError, FirebaseAuthError, FirebaseConfigError) as e:
        st.query_params.clear()
        st.error(str(e))
        return

    save_session(user)
    st.query_params.clear()
    st.rerun()


# ─────────────────────────────────────────────────────────────────
#  UI — STYLES + BRAND PANEL
# ─────────────────────────────────────────────────────────────────

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }
html, body, .stApp, [class*="css"] { font-family: 'Inter', sans-serif !important; }
.stApp { background: #f7f4f0 !important; }

.block-container {
    padding: 2rem 1rem !important;
    max-width: 1100px !important;
}

[data-testid="stHorizontalBlock"] {
    background: #fff;
    border-radius: 16px;
    box-shadow: 0 20px 60px -20px rgba(0,0,0,0.15);
    overflow: hidden;
    align-items: stretch !important;
}
[data-testid="stHorizontalBlock"] > div:first-child {
    background: linear-gradient(160deg, #faf8f5 0%, #ede8e0 100%);
    padding: 48px 44px !important;
}
[data-testid="stHorizontalBlock"] > div:last-child {
    background: #ffffff;
    padding: 48px 44px !important;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 8px !important;
    border-bottom: 2px solid #ede8e0 !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #9ca3af !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    padding: 10px 16px !important;
    border-bottom: 2px solid transparent !important;
    margin-bottom: -2px !important;
}
.stTabs [aria-selected="true"] {
    color: #9D174D !important;
    border-bottom-color: #9D174D !important;
}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] { display: none !important; }

.stTextInput label p, .stTextInput label, .stCheckbox label p {
    color: #111827 !important;
    font-weight: 500 !important;
    font-size: 14px !important;
}
.stTextInput input {
    background: #fff !important;
    border: 1.5px solid #e5e7eb !important;
    border-radius: 10px !important;
    color: #111827 !important;
    padding: 11px 14px !important;
    font-size: 14px !important;
}
.stTextInput input:focus {
    border-color: #9D174D !important;
    box-shadow: 0 0 0 3px rgba(157,23,77,0.10) !important;
}
.stTextInput input::placeholder { color: #d1d5db !important; }

.stFormSubmitButton > button, .stButton > button {
    background: #9D174D !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 12px 20px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    width: 100% !important;
    transition: background .18s, transform .15s, box-shadow .15s !important;
}
.stFormSubmitButton > button:hover, .stButton > button:hover {
    background: #7d1340 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(157,23,77,0.30) !important;
}

[data-testid="stForm"] {
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
}

.snti-logo { display:flex; align-items:center; gap:12px; margin-bottom:56px; }
.snti-logo-icon {
    width:44px; height:44px; border-radius:12px;
    background:#9D174D; color:#fff;
    display:flex; align-items:center; justify-content:center;
    font-size:22px; box-shadow:0 8px 20px rgba(157,23,77,.25);
}
.snti-logo-text { font-weight:700; font-size:18px; color:#111827; }
.snti-eyebrow { color:#9D174D; font-size:11px; font-weight:700; letter-spacing:2px; text-transform:uppercase; }
.snti-title { font-size:34px; font-weight:700; line-height:1.15; margin:10px 0 14px; color:#111827; }
.snti-title .accent { color:#9D174D; }
.snti-subtitle { color:#6b7280; font-size:14px; line-height:1.6; margin-bottom:36px; }
.snti-feature { display:flex; gap:14px; margin-bottom:18px; }
.snti-feature-icon {
    width:40px; height:40px; border-radius:10px;
    background:#fdf2f6; color:#9D174D;
    display:flex; align-items:center; justify-content:center;
    font-size:18px; flex-shrink:0;
}
.snti-feature-title { font-weight:600; font-size:14px; color:#111827; }
.snti-feature-desc { color:#6b7280; font-size:13px; line-height:1.5; }
.snti-footer { text-align:center; margin-top:24px; color:#9ca3af; font-size:12px; }

.social-row { display:flex; flex-direction:column; gap:10px; margin-top:8px; }
.social-btn {
    display:flex; align-items:center; justify-content:center; gap:10px;
    padding:11px 16px; border-radius:10px;
    border:1.5px solid #e5e7eb; background:#fff;
    color:#374151 !important; font-weight:500; font-size:14px;
    text-decoration:none !important;
    transition:border-color .18s, background .18s, box-shadow .15s;
}
.social-btn:hover {
    border-color:#9D174D; background:#fdf7f9;
    box-shadow:0 2px 8px rgba(157,23,77,.08);
}
.social-divider {
    display:flex; align-items:center; gap:12px;
    margin:18px 0 10px; color:#c4b9b0; font-size:11px;
    font-weight:600; text-transform:uppercase; letter-spacing:1.2px;
}
.social-divider::before, .social-divider::after {
    content:''; flex:1; height:1px; background:#ede8e0;
}
</style>
"""

LEFT = """
<div class="snti-logo">
  <div class="snti-logo-icon">🤖</div>
  <div class="snti-logo-text">SNTI AI</div>
</div>
<div class="snti-eyebrow">Welcome Back</div>
<h1 class="snti-title">Sign in to <span class="accent">SNTI AI</span> Assistant</h1>
<p class="snti-subtitle">Access your workspace to continue research, analyze data,
write code, and more with your AI assistant.</p>
<div class="snti-feature">
  <div class="snti-feature-icon">🛡️</div>
  <div>
    <div class="snti-feature-title">Secure & Private</div>
    <div class="snti-feature-desc">Enterprise-grade security to keep your data safe.</div>
  </div>
</div>
<div class="snti-feature">
  <div class="snti-feature-icon">⚡</div>
  <div>
    <div class="snti-feature-title">AI-Powered Productivity</div>
    <div class="snti-feature-desc">Research, code, analyze, and innovate faster.</div>
  </div>
</div>
<div class="snti-feature">
  <div class="snti-feature-icon">☁️</div>
  <div>
    <div class="snti-feature-title">Sync Everywhere</div>
    <div class="snti-feature-desc">Access your workspace across all your devices.</div>
  </div>
</div>
"""

PROVIDER_ICONS = {
    "google": '<svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.99.66-2.25 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09a6.6 6.6 0 010-4.18V7.07H2.18a11 11 0 000 9.86l3.66-2.84z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38z"/></svg>',
    "github": '<svg width="18" height="18" viewBox="0 0 24 24" fill="#181717"><path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.1.79-.25.79-.56v-2c-3.2.7-3.87-1.37-3.87-1.37-.52-1.33-1.28-1.69-1.28-1.69-1.05-.72.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.7 1.26 3.36.96.1-.75.4-1.26.73-1.55-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.29 1.18-3.1-.12-.29-.51-1.46.11-3.05 0 0 .97-.31 3.18 1.18a11 11 0 015.78 0c2.21-1.49 3.18-1.18 3.18-1.18.62 1.59.23 2.76.11 3.05.74.81 1.18 1.84 1.18 3.1 0 4.42-2.7 5.4-5.27 5.68.41.36.78 1.06.78 2.14v3.17c0 .31.21.67.8.56C20.21 21.39 23.5 17.08 23.5 12 23.5 5.65 18.35.5 12 .5z"/></svg>',
    "microsoft": '<svg width="18" height="18" viewBox="0 0 24 24"><path fill="#F25022" d="M2 2h9.5v9.5H2z"/><path fill="#7FBA00" d="M12.5 2H22v9.5h-9.5z"/><path fill="#00A4EF" d="M2 12.5h9.5V22H2z"/><path fill="#FFB900" d="M12.5 12.5H22V22h-9.5z"/></svg>',
}


# ─────────────────────────────────────────────────────────────────
#  UI — FORMS
# ─────────────────────────────────────────────────────────────────

def render_social_buttons() -> None:
    st.markdown('<div class="social-divider">or continue with</div>', unsafe_allow_html=True)
    html = '<div class="social-row">'
    any_ready = False
    for provider, cfg in PROVIDERS.items():
        if not _provider_ready(provider):
            continue
        any_ready = True
        url = _build_authorize_url(provider)
        html += (
            f'<a class="social-btn" href="{url}" target="_self">'
            f'{PROVIDER_ICONS[provider]}<span>Continue with {cfg["name"]}</span></a>'
        )
    html += "</div>"
    if not any_ready:
        st.caption("⚙️ Social sign-in not configured. Set provider client IDs in `.env`.")
    else:
        st.markdown(html, unsafe_allow_html=True)


def _sign_in_form() -> None:
    with st.form("signin_form", border=False):
        email = st.text_input("Email address", placeholder="you@example.com")
        password = st.text_input("Password", type="password",
                                 placeholder="Enter your password")
        st.checkbox("Keep me signed in", value=True)
        submitted = st.form_submit_button("Sign in")
    if submitted:
        try:
            save_session(_sign_in(email.strip(), password))
            st.rerun()
        except (FirebaseAuthError, FirebaseConfigError) as e:
            st.error(str(e))


def _create_form() -> None:
    with st.form("create_form", border=False):
        name = st.text_input("Display name", placeholder="Your name")
        email = st.text_input("Email address", placeholder="you@example.com", key="ce")
        password = st.text_input("Password", type="password",
                                 placeholder="Create a password", key="cp")
        confirm = st.text_input("Confirm password", type="password",
                                placeholder="Confirm your password")
        submitted = st.form_submit_button("Create account")
    if submitted:
        if len(password) < 8:
            st.error("Password must be at least 8 characters."); return
        if password != confirm:
            st.error("Passwords do not match."); return
        try:
            save_session(_create_account(email.strip(), password, name.strip()))
            st.rerun()
        except (FirebaseAuthError, FirebaseConfigError) as e:
            st.error(str(e))


def _reset_form() -> None:
    st.markdown(
        "<p style='color:#6b7280;font-size:14px;margin-bottom:16px;'>"
        "Enter your email and we'll send you a reset link.</p>",
        unsafe_allow_html=True,
    )
    with st.form("reset_form", border=False):
        email = st.text_input("Email address", placeholder="you@example.com", key="re")
        submitted = st.form_submit_button("Send reset link")
    if submitted:
        try:
            _send_password_reset(email.strip())
            st.success("✓ Password reset email sent.")
        except (FirebaseAuthError, FirebaseConfigError) as e:
            st.error(str(e))


# ─────────────────────────────────────────────────────────────────
#  PUBLIC API
# ─────────────────────────────────────────────────────────────────

def require_login(app_name: str = "SNTI AI Assistant") -> dict:
    # 1. Logout
    if st.query_params.get("logout") == "1":
        clear_session()
        st.query_params.clear()
        st.rerun()

    # 2. OAuth callback (Google/GitHub/Microsoft)
    handle_oauth_callback()

    # 3. Auto-refresh + hydrate from disk
    try:
        ensure_fresh_token()
    except SessionExpired as e:
        clear_session()
        st.warning(str(e))

    # 4. Live session?
    user = get_current_user()
    if user:
        return user

    # 5. Login UI
    st.markdown(CSS, unsafe_allow_html=True)
    if not _firebase_api_key():
        st.warning("**Firebase not configured.** Set `FIREBASE_WEB_API_KEY` in `.env`.")
        st.code("FIREBASE_WEB_API_KEY=your_key\nFIREBASE_PROJECT_ID=your_project",
                language="env")
        st.stop()

    left, right = st.columns([1.1, 1], gap="small")
    with left:
        st.markdown(LEFT, unsafe_allow_html=True)
    with right:
        t1, t2, t3 = st.tabs(["Sign in", "Create account", "Reset password"])
        with t1:
            _sign_in_form()
            render_social_buttons()
        with t2:
            _create_form()
            render_social_buttons()
        with t3:
            _reset_form()
        st.markdown(
            "<div class='snti-footer'>🛡️ Protected by Firebase Authentication</div>",
            unsafe_allow_html=True,
        )

    st.stop()


def logout_link(label: str = "Logout") -> str:
    return f'<a href="?logout=1">{label}</a>'



# ─────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    st.set_page_config(
        page_title="SNTI AI Assistant",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    user = require_login()

    # Your app starts here ──────────────────────────────
    st.title(f"Hello, {user['name']} 👋")
    st.write(f"**Email:** {user['email']}")
    st.write(f"**Provider:** {user['provider']}")
    st.markdown(logout_link("Logout"), unsafe_allow_html=True)
