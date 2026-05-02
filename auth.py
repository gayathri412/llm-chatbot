import html
import os
import secrets
from typing import Any
from urllib.parse import urlencode

import requests
import streamlit as st

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False


load_dotenv()

FIREBASE_AUTH_BASE_URL = "https://identitytoolkit.googleapis.com/v1"


class FirebaseAuthError(Exception):
    pass


class FirebaseConfigError(Exception):
    pass


class SocialAuthError(Exception):
    pass


class SocialConfigError(Exception):
    pass


class OIDCAuthError(Exception):
    pass


class OIDCConfigError(Exception):
    pass


def _get_secret_value(section: str, key: str) -> str | None:
    try:
        values = st.secrets.get(section, {})
        if hasattr(values, "get"):
            return values.get(key) or None
    except Exception:
        pass
    return None


def _auth_provider() -> str:
    return (os.getenv("AUTH_PROVIDER") or _get_secret_value("auth", "provider") or "firebase").lower()


def _firebase_api_key() -> str | None:
    return (
        os.getenv("FIREBASE_WEB_API_KEY")
        or _get_secret_value("firebase", "web_api_key")
    )


def _firebase_project_id() -> str | None:
    return (
        os.getenv("FIREBASE_PROJECT_ID")
        or os.getenv("GCP_PROJECT_ID")
        or _get_secret_value("firebase", "project_id")
    )


def _oidc_secret(key: str) -> str | None:
    env_name = f"OIDC_{key.upper()}"
    return os.getenv(env_name) or _get_secret_value("oidc", key)


def _oidc_provider_name() -> str:
    return _oidc_secret("provider_name") or "Enterprise SSO"


def _oidc_discovery_url() -> str | None:
    return _oidc_secret("discovery_url")


def _oidc_client_id() -> str | None:
    return _oidc_secret("client_id")


def _oidc_client_secret() -> str | None:
    return _oidc_secret("client_secret")


def _oidc_redirect_uri() -> str | None:
    redirect_uri = _oidc_secret("redirect_uri")
    if redirect_uri:
        return redirect_uri

    app_base_url = os.getenv("APP_BASE_URL") or _get_secret_value("app", "base_url")
    return app_base_url.rstrip("/") if app_base_url else None


def _oidc_scopes() -> str:
    return _oidc_secret("scopes") or "openid profile email"


def _oidc_list_secret(key: str) -> list[str]:
    raw = _oidc_secret(key) or ""
    return [item.strip().lower() for item in raw.split(",") if item.strip()]


def _oidc_ready() -> bool:
    return all([
        _oidc_discovery_url(),
        _oidc_client_id(),
        _oidc_client_secret(),
        _oidc_redirect_uri(),
    ])


def _oidc_discovery() -> dict[str, Any]:
    discovery_url = _oidc_discovery_url()
    if not discovery_url:
        raise OIDCConfigError("OIDC_DISCOVERY_URL is not configured.")

    response = requests.get(discovery_url, timeout=20)
    if not response.ok:
        raise OIDCConfigError(f"Could not load OIDC discovery document: {response.status_code}")

    return response.json()


def _friendly_firebase_error(code: str) -> str:
    messages = {
        "EMAIL_EXISTS": "An account already exists for this email.",
        "EMAIL_NOT_FOUND": "No account was found for this email.",
        "INVALID_LOGIN_CREDENTIALS": "The email or password is incorrect.",
        "INVALID_PASSWORD": "The email or password is incorrect.",
        "MISSING_PASSWORD": "Please enter a password.",
        "USER_DISABLED": "This account has been disabled.",
        "WEAK_PASSWORD : Password should be at least 6 characters": (
            "Use a stronger password with at least 8 characters."
        ),
        "TOO_MANY_ATTEMPTS_TRY_LATER": (
            "Too many attempts. Please wait a moment and try again."
        ),
        "INVALID_EMAIL": "Please enter a valid email address.",
        "OPERATION_NOT_ALLOWED": (
            "Email/password sign-in is not enabled in Firebase. "
            "Open Firebase Authentication > Sign-in method and enable Email/Password."
        ),
        "PASSWORD_LOGIN_DISABLED": (
            "Email/password sign-in is not enabled in Firebase. "
            "Open Firebase Authentication > Sign-in method and enable Email/Password."
        ),
        "CONFIGURATION_NOT_FOUND": (
            "Firebase Authentication is not initialized for this project. "
            "Open Firebase Authentication, click Get started, and enable Email/Password."
        ),
        "API_KEY_INVALID": "The Firebase Web API key is invalid. Copy the apiKey from your Web app config again.",
        "INVALID_API_KEY": "The Firebase Web API key is invalid. Copy the apiKey from your Web app config again.",
        "PROJECT_NOT_FOUND": "Firebase could not find this project. Check FIREBASE_PROJECT_ID in .env.",
        "ADMIN_ONLY_OPERATION": "Account creation is disabled for this Firebase project.",
    }
    return messages.get(code, f"Firebase error: {code or 'unknown error'}")


def _firebase_request(endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
    api_key = _firebase_api_key()
    if not api_key:
        raise FirebaseConfigError("FIREBASE_WEB_API_KEY is not configured.")

    url = f"{FIREBASE_AUTH_BASE_URL}/{endpoint}?key={api_key}"
    response = requests.post(url, json=payload, timeout=20)

    try:
        data = response.json()
    except ValueError:
        data = {}

    if response.ok:
        return data

    error_code = data.get("error", {}).get("message", "")
    raise FirebaseAuthError(_friendly_firebase_error(error_code))


def _user_from_firebase(data: dict[str, Any]) -> dict[str, str]:
    email = data.get("email", "")
    display_name = data.get("displayName") or email.split("@")[0] or "User"
    uid = data.get("localId", "")
    return {
        "provider": "firebase",
        "user_id": uid or email,
        "username": email,
        "email": email,
        "name": display_name,
        "id_token": data.get("idToken", ""),
        "refresh_token": data.get("refreshToken", ""),
    }


def _sign_in(email: str, password: str) -> dict[str, str]:
    data = _firebase_request(
        "accounts:signInWithPassword",
        {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        },
    )
    return _user_from_firebase(data)


def _create_account(email: str, password: str, display_name: str) -> dict[str, str]:
    data = _firebase_request(
        "accounts:signUp",
        {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        },
    )

    if display_name:
        data = _firebase_request(
            "accounts:update",
            {
                "idToken": data["idToken"],
                "displayName": display_name,
                "returnSecureToken": True,
            },
        )

    return _user_from_firebase(data)


def _send_password_reset(email: str) -> None:
    _firebase_request(
        "accounts:sendOobCode",
        {
            "requestType": "PASSWORD_RESET",
            "email": email,
        },
    )


def _oidc_authorization_url() -> str:
    discovery = _oidc_discovery()
    authorization_endpoint = discovery.get("authorization_endpoint")
    if not authorization_endpoint:
        raise OIDCConfigError("OIDC discovery document is missing authorization_endpoint.")

    state = secrets.token_urlsafe(24)
    nonce = secrets.token_urlsafe(24)
    st.session_state.oidc_state = state
    st.session_state.oidc_nonce = nonce

    prompt = _oidc_secret("prompt")
    params = {
        "client_id": _oidc_client_id(),
        "response_type": "code",
        "scope": _oidc_scopes(),
        "redirect_uri": _oidc_redirect_uri(),
        "state": state,
        "nonce": nonce,
    }
    if prompt:
        params["prompt"] = prompt

    return f"{authorization_endpoint}?{urlencode(params)}"


def _exchange_oidc_code(code: str, state: str) -> dict[str, Any]:
    expected_state = st.session_state.get("oidc_state")
    if not expected_state or state != expected_state:
        raise OIDCAuthError("SSO state check failed. Please try signing in again.")

    discovery = _oidc_discovery()
    token_endpoint = discovery.get("token_endpoint")
    userinfo_endpoint = discovery.get("userinfo_endpoint")
    if not token_endpoint:
        raise OIDCConfigError("OIDC discovery document is missing token_endpoint.")
    if not userinfo_endpoint:
        raise OIDCConfigError("OIDC discovery document is missing userinfo_endpoint.")

    token_response = requests.post(
        token_endpoint,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": _oidc_redirect_uri(),
            "client_id": _oidc_client_id(),
            "client_secret": _oidc_client_secret(),
        },
        headers={"Accept": "application/json"},
        timeout=20,
    )
    try:
        token_data = token_response.json()
    except ValueError:
        token_data = {}

    if not token_response.ok:
        error = token_data.get("error_description") or token_data.get("error") or token_response.text
        raise OIDCAuthError(f"SSO token exchange failed: {error}")

    access_token = token_data.get("access_token")
    if not access_token:
        raise OIDCAuthError("SSO provider did not return an access token.")

    userinfo_response = requests.get(
        userinfo_endpoint,
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        timeout=20,
    )
    try:
        userinfo = userinfo_response.json()
    except ValueError:
        userinfo = {}

    if not userinfo_response.ok:
        error = userinfo.get("error_description") or userinfo.get("error") or userinfo_response.text
        raise OIDCAuthError(f"SSO user profile lookup failed: {error}")

    userinfo["_tokens"] = token_data
    return userinfo


def _user_from_oidc(data: dict[str, Any]) -> dict[str, Any]:
    tokens = data.get("_tokens", {})
    email = (
        data.get("email")
        or data.get("preferred_username")
        or data.get("upn")
        or data.get("unique_name")
        or ""
    )
    subject = data.get("sub") or data.get("oid") or email
    display_name = data.get("name") or data.get("given_name") or email.split("@")[0] or "User"
    groups = data.get("groups") if isinstance(data.get("groups"), list) else []
    roles = data.get("roles") if isinstance(data.get("roles"), list) else []

    return {
        "provider": "oidc",
        "user_id": str(subject),
        "username": str(email or subject),
        "email": str(email),
        "name": str(display_name),
        "groups": groups,
        "roles": roles,
        "id_token": tokens.get("id_token", ""),
        "access_token": tokens.get("access_token", ""),
        "refresh_token": tokens.get("refresh_token", ""),
    }


def _validate_oidc_access(user: dict[str, Any]) -> None:
    allowed_emails = _oidc_list_secret("allowed_emails")
    allowed_domains = _oidc_list_secret("allowed_domains")
    if not allowed_emails and not allowed_domains:
        return

    email = str(user.get("email") or "").lower()
    domain = email.rsplit("@", 1)[-1] if "@" in email else ""

    if email in allowed_emails or domain in allowed_domains:
        return

    raise OIDCAuthError("Your SSO account is not allowed to access this app.")


def _clear_auth_session() -> None:
    for key in (
        "authenticated",
        "auth_provider",
        "auth_user",
        "auth_user_id",
        "auth_email",
        "auth_name",
        "auth_groups",
        "auth_roles",
        "firebase_id_token",
        "firebase_refresh_token",
        "oidc_id_token",
        "oidc_access_token",
        "oidc_refresh_token",
        "oidc_state",
        "oidc_nonce",
    ):
        st.session_state.pop(key, None)


def _set_auth_session(user: dict[str, Any]) -> None:
    st.session_state.authenticated = True
    st.session_state.auth_provider = user.get("provider", _auth_provider())
    st.session_state.auth_user = user["username"]
    st.session_state.auth_user_id = user["user_id"]
    st.session_state.auth_email = user["email"]
    st.session_state.auth_name = user["name"]
    st.session_state.auth_groups = user.get("groups", [])
    st.session_state.auth_roles = user.get("roles", [])
    if user.get("provider") == "oidc":
        st.session_state.oidc_id_token = user.get("id_token", "")
        st.session_state.oidc_access_token = user.get("access_token", "")
        st.session_state.oidc_refresh_token = user.get("refresh_token", "")
    else:
        st.session_state.firebase_id_token = user.get("id_token", "")
        st.session_state.firebase_refresh_token = user.get("refresh_token", "")


def get_current_user() -> dict[str, str] | None:
    if not st.session_state.get("authenticated"):
        return None

    return {
        "provider": st.session_state.get("auth_provider", "firebase"),
        "user_id": st.session_state.get("auth_user_id", ""),
        "username": st.session_state.get("auth_user", ""),
        "email": st.session_state.get("auth_email", ""),
        "name": st.session_state.get("auth_name", ""),
        "groups": st.session_state.get("auth_groups", []),
        "roles": st.session_state.get("auth_roles", []),
    }





def _social_provider_config(provider: str) -> dict[str, str]:
    configs = {
        "google": {
            "name": "Google",
            "firebase_provider_id": "google.com",
            "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_endpoint": "https://oauth2.googleapis.com/token",
            "scope": "openid email profile",
            "credential_field": "id_token",
        },
        "github": {
            "name": "GitHub",
            "firebase_provider_id": "github.com",
            "authorization_endpoint": "https://github.com/login/oauth/authorize",
            "token_endpoint": "https://github.com/login/oauth/access_token",
            "scope": "read:user user:email",
            "credential_field": "access_token",
        },
    }
    if provider not in configs:
        raise SocialConfigError(f"Unsupported social provider: {provider}")
    return configs[provider]


def _social_secret(provider: str, key: str) -> str | None:
    provider_key = provider.upper()
    key_name = key.upper()
    return (
        os.getenv(f"{provider_key}_{key_name}")
        or _get_secret_value(provider, key)
        or _get_secret_value(f"{provider}_oauth", key)
        or _get_secret_value("oauth", f"{provider}_{key}")
        or _get_secret_value("auth", f"{provider}_{key}")
    )


def _social_redirect_uri(provider: str) -> str | None:
    return (
        _social_secret(provider, "redirect_uri")
        or os.getenv("OAUTH_REDIRECT_URI")
        or _get_secret_value("oauth", "redirect_uri")
        or os.getenv("APP_BASE_URL")
        or _get_secret_value("app", "base_url")
    )


def _social_oauth_ready(provider: str) -> bool:
    return all([
        _social_secret(provider, "client_id"),
        _social_secret(provider, "client_secret"),
        _social_redirect_uri(provider),
    ])


def _social_authorization_url(provider: str) -> str:
    config = _social_provider_config(provider)
    client_id = _social_secret(provider, "client_id")
    redirect_uri = _social_redirect_uri(provider)
    if not client_id or not _social_secret(provider, "client_secret") or not redirect_uri:
        raise SocialConfigError(
            f"{config['name']} sign-in needs {provider.upper()}_CLIENT_ID, "
            f"{provider.upper()}_CLIENT_SECRET, and APP_BASE_URL."
        )

    state = f"{provider}:{secrets.token_urlsafe(24)}"
    states = st.session_state.setdefault("social_oauth_states", {})
    states[state] = provider
    if len(states) > 20:
        for old_state in list(states)[:-20]:
            states.pop(old_state, None)

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri.rstrip("/"),
        "response_type": "code",
        "scope": config["scope"],
        "state": state,
    }
    if provider == "google":
        params["prompt"] = "select_account"
    if provider == "github":
        params["allow_signup"] = "true"

    return f"{config['authorization_endpoint']}?{urlencode(params)}"


def _exchange_social_oauth_code(provider: str, code: str) -> dict[str, str]:
    config = _social_provider_config(provider)
    client_id = _social_secret(provider, "client_id")
    client_secret = _social_secret(provider, "client_secret")
    redirect_uri = _social_redirect_uri(provider)
    if not client_id or not client_secret or not redirect_uri:
        raise SocialConfigError(
            f"{config['name']} sign-in is missing OAuth client settings."
        )

    token_response = requests.post(
        config["token_endpoint"],
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri.rstrip("/"),
            "client_id": client_id,
            "client_secret": client_secret,
        },
        headers={"Accept": "application/json"},
        timeout=20,
    )
    try:
        token_data = token_response.json()
    except ValueError:
        token_data = {}

    if not token_response.ok:
        error = token_data.get("error_description") or token_data.get("error") or token_response.text
        raise SocialAuthError(f"{config['name']} sign-in failed: {error}")

    credential_field = config["credential_field"]
    credential_value = token_data.get(credential_field)
    if provider == "google" and not credential_value:
        credential_field = "access_token"
        credential_value = token_data.get("access_token")
    if not credential_value:
        raise SocialAuthError(f"{config['name']} did not return a usable OAuth token.")

    firebase_data = _firebase_request(
        "accounts:signInWithIdp",
        {
            "postBody": urlencode({
                credential_field: credential_value,
                "providerId": config["firebase_provider_id"],
            }),
            "requestUri": redirect_uri.rstrip("/"),
            "returnIdpCredential": True,
            "returnSecureToken": True,
        },
    )
    user = _user_from_firebase(firebase_data)
    user["provider"] = config["firebase_provider_id"]
    return user


def _handle_social_oauth_callback() -> None:
    code = st.query_params.get("code")
    state = st.query_params.get("state")
    error = st.query_params.get("error")

    if not state or not any(str(state).startswith(f"{provider}:") for provider in ("google", "github")):
        return

    if error:
        description = st.query_params.get("error_description") or error
        st.query_params.clear()
        st.error(f"Social sign-in failed: {description}")
        return

    if not code:
        return

    states = st.session_state.get("social_oauth_states", {})
    provider = states.pop(state, None)
    if not provider:
        st.query_params.clear()
        st.error("Social sign-in expired. Please try again.")
        return

    try:
        user = _exchange_social_oauth_code(provider, code)
    except (FirebaseAuthError, FirebaseConfigError, SocialAuthError, SocialConfigError) as exc:
        st.query_params.clear()
        st.error(str(exc))
        return

    _set_auth_session(user)
    st.query_params.clear()
    st.rerun()


def _render_auth_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        #MainMenu, footer, header { visibility: hidden; }
        .stApp { 
            background: linear-gradient(135deg, #faf8f5 0%, #f5f0e8 100%) !important; 
            color: #1a1a1a;
            font-family: 'Inter', sans-serif;
        }
        
        /* Hide default Streamlit block container */
        [data-testid="block-container"] {
            max-width: 100% !important;
            padding: 0 !important;
        }
        
        /* Main auth container - split layout */
        .auth-container {
            display: flex;
            min-height: 100vh;
            width: 100%;
        }
        
        /* Left panel - dark */
        .auth-left {
            flex: 1;
            background: #faf8f5;
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 60px 80px;
            position: relative;
            overflow: hidden;
            min-height: 100vh;
        }
        
        .auth-left::before {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 200px;
            background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1440 320'%3E%3Cpath fill='%239D174D' fill-opacity='0.08' d='M0,96L48,112C96,128,192,160,288,160C384,160,480,128,576,122.7C672,117,768,139,864,154.7C960,171,1056,181,1152,165.3C1248,149,1344,107,1392,85.3L1440,64L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z'%3E%3C/path%3E%3C/svg%3E") no-repeat bottom;
            background-size: cover;
        }
        
        .auth-logo {
            position: absolute;
            top: 32px;
            left: 40px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .auth-logo-icon {
            width: 44px;
            height: 44px;
            background: #9D174D;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
        }
        
        .auth-logo-text {
            font-size: 22px;
            font-weight: 700;
            color: #9D174D;
            letter-spacing: -0.5px;
        }
        
        .auth-welcome {
            max-width: 420px;
            position: relative;
            z-index: 1;
            margin-top: 40px;
        }
        
        .auth-welcome-label {
            color: #9D174D;
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-bottom: 16px;
        }
        
        .auth-welcome h1 {
            color: #1e1b4b;
            font-size: 36px;
            font-weight: 700;
            margin: 0 0 16px 0;
            line-height: 1.2;
        }
        
        .auth-welcome p {
            color: #6b7280;
            font-size: 15px;
            line-height: 1.6;
            margin: 0 0 40px 0;
        }
        
        .auth-features {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        
        .auth-feature {
            display: flex;
            align-items: flex-start;
            gap: 16px;
        }
        
        .auth-feature-icon {
            width: 48px;
            height: 48px;
            background: rgba(157, 23, 77, 0.08);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            flex-shrink: 0;
        }
        
        .auth-feature-text h3 {
            color: #1e1b4b;
            font-size: 15px;
            font-weight: 600;
            margin: 0 0 4px 0;
        }
        
        .auth-feature-text p {
            color: #9ca3af;
            font-size: 14px;
            margin: 0;
            line-height: 1.4;
        }
        
        /* Right panel - white */
        .auth-right {
            flex: 1;
            background: #ffffff;
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 60px 80px;
            max-width: 520px;
            min-height: 100vh;
            box-shadow: -4px 0 24px rgba(0,0,0,0.03);
        }
        
        /* Ensure Streamlit content shows in right panel */
        .auth-right > div {
            width: 100%;
        }
        
        /* Make sure Streamlit forms and tabs appear in the flow */
        .auth-right .stForm,
        .auth-right .stTabs,
        .auth-right [data-testid="stForm"],
        .auth-right [data-testid="stTabs"] {
            width: 100% !important;
        }
        
        .auth-right [data-baseweb="tab-list"] {
            gap: 32px !important;
            border-bottom: 1px solid #e5e5e5 !important;
        }
        
        .auth-right [data-baseweb="tab"] {
            padding: 12px 0 !important;
            font-size: 14px !important;
            font-weight: 500 !important;
            color: #666 !important;
            background: transparent !important;
            border-bottom: 2px solid transparent !important;
        }
        
        .auth-right [aria-selected="true"] {
            color: #9D174D !important;
            border-bottom-color: #9D174D !important;
        }
        
        .auth-tabs {
            display: flex;
            gap: 32px;
            margin-bottom: 32px;
            border-bottom: 1px solid #e5e5e5;
        }
        
        .auth-tab {
            padding: 12px 0;
            font-size: 14px;
            font-weight: 500;
            color: #666;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
            background: none;
            border-top: none;
            border-left: none;
            border-right: none;
        }
        
        .auth-tab.active {
            color: #9D174D;
            border-bottom-color: #9D174D;
        }
        
        .auth-form {
            width: 100%;
        }
        
        .auth-input-label {
            display: block;
            font-size: 13px;
            font-weight: 500;
            color: #333;
            margin-bottom: 8px;
        }
        
        .stTextInput input {
            background: #fff;
            border: 1px solid #e0e0e0;
            color: #333;
            border-radius: 10px;
            padding: 12px 16px;
            font-size: 14px;
            width: 100%;
        }
        
        .stTextInput input:focus {
            border-color: #9D174D;
            box-shadow: 0 0 0 3px rgba(157, 23, 77, 0.1);
        }
        
        .auth-checkbox-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin: 20px 0;
        }
        
        .auth-checkbox {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            color: #666;
        }
        
        .auth-forgot {
            font-size: 13px;
            color: #9D174D;
            text-decoration: none;
            font-weight: 500;
        }
        
        .auth-forgot:hover {
            text-decoration: underline;
        }
        
        .stButton button {
            background: #9D174D;
            border: none;
            color: #fff;
            font-weight: 600;
            font-size: 14px;
            border-radius: 10px;
            padding: 14px 24px;
            width: 100%;
            transition: all 0.2s;
        }
        
        .stButton button:hover {
            background: #7a1240;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(157, 23, 77, 0.3);
        }
        
        .auth-divider {
            display: flex;
            align-items: center;
            margin: 28px 0;
            color: #999;
            font-size: 13px;
        }
        
        .auth-divider::before,
        .auth-divider::after {
            content: '';
            flex: 1;
            height: 1px;
            background: #e0e0e0;
        }
        
        .auth-divider span {
            padding: 0 16px;
        }
        
        .auth-social-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            width: 100%;
            padding: 12px 16px;
            border-radius: 10px;
            border: 1px solid #e0e0e0;
            background: #fff;
            color: #333;
            font-weight: 500;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.2s;
            margin-bottom: 12px;
        }
        
        .auth-social-btn:hover {
            border-color: #9D174D;
            background: #fafafa;
        }
        
        .auth-social-btn img {
            width: 20px;
            height: 20px;
        }
        
        .auth-footer {
            text-align: center;
            margin-top: 32px;
            color: #999;
            font-size: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }
        
        .auth-footer-icon {
            color: #9D174D;
        }
        
        /* Streamlit tabs styling override */
        .stTabs [data-baseweb="tab-list"] {
            gap: 32px;
            border-bottom: 1px solid #e5e5e5;
        }
        
        .stTabs [data-baseweb="tab"] {
            padding: 12px 0;
            font-size: 14px;
            font-weight: 500;
            color: #666;
            background: transparent;
            border-bottom: 2px solid transparent;
        }
        
        .stTabs [aria-selected="true"] {
            color: #9D174D !important;
            border-bottom-color: #9D174D !important;
        }
        
        /* Hide default form borders */
        [data-testid="stForm"] {
            border: none !important;
            padding: 0 !important;
        }
        
        /* Responsive */
        @media (max-width: 900px) {
            .auth-left {
                display: none;
            }
            .auth-right {
                max-width: 100%;
                padding: 40px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_auth_panel(title: str, message: str) -> None:
    # Left panel with welcome content
    st.markdown(
        """
        <div class="auth-container">
            <div class="auth-left">
                <div class="auth-logo">
                    <div class="auth-logo-icon">🤖</div>
                    <span class="auth-logo-text">SNTI AI</span>
                </div>
                <div class="auth-welcome">
                    <div class="auth-welcome-label">Welcome Back</div>
                    <h1>Sign in to <span style="color: #9D174D;">SNTI AI</span> Assistant</h1>
                    <p>Access your workspace to continue research, analyze data, write code, and more with your AI assistant.</p>
                    <div class="auth-features">
                        <div class="auth-feature">
                            <div class="auth-feature-icon">🛡️</div>
                            <div class="auth-feature-text">
                                <h3>Secure & Private</h3>
                                <p>Enterprise-grade security to keep your data safe.</p>
                            </div>
                        </div>
                        <div class="auth-feature">
                            <div class="auth-feature-icon">⚡</div>
                            <div class="auth-feature-text">
                                <h3>AI-Powered Productivity</h3>
                                <p>Research, code, analyze, and innovate faster.</p>
                            </div>
                        </div>
                        <div class="auth-feature">
                            <div class="auth-feature-icon">☁️</div>
                            <div class="auth-feature-text">
                                <h3>Sync Everywhere</h3>
                                <p>Access your workspace across all your devices.</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="auth-right">
        """,
        unsafe_allow_html=True,
    )


def _render_firebase_setup_message() -> None:
    project_hint = _firebase_project_id() or "your Firebase project"
    _render_auth_panel(
        "Connect Firebase",
        (
            "Firebase Authentication is enabled, but the app needs your Firebase Web API key. "
            f"Add FIREBASE_WEB_API_KEY for {project_hint}, then restart Streamlit."
        ),
    )
    st.code(
        "FIREBASE_WEB_API_KEY=your_firebase_web_api_key\n"
        "FIREBASE_PROJECT_ID=your_firebase_project_id",
        language="env",
    )
    st.stop()


def _render_oidc_setup_message() -> None:
    _render_auth_panel(
        "Connect Enterprise SSO",
        (
            "Enterprise SSO is selected, but OIDC settings are missing. "
            "Configure Azure AD or Okta values, then restart Streamlit."
        ),
    )
    st.code(
        "AUTH_PROVIDER=oidc\n"
        "OIDC_PROVIDER_NAME=Azure AD\n"
        "OIDC_DISCOVERY_URL=https://login.microsoftonline.com/<tenant-id>/v2.0/.well-known/openid-configuration\n"
        "OIDC_CLIENT_ID=your_client_id\n"
        "OIDC_CLIENT_SECRET=your_client_secret\n"
        "OIDC_REDIRECT_URI=http://localhost:8501\n"
        "OIDC_SCOPES=openid profile email",
        language="env",
    )
    st.stop()


def _handle_oidc_callback() -> None:
    code = st.query_params.get("code")
    state = st.query_params.get("state")
    error = st.query_params.get("error")

    if error:
        description = st.query_params.get("error_description") or error
        st.error(f"SSO sign-in failed: {description}")
        return

    if not code:
        return

    try:
        user = _user_from_oidc(_exchange_oidc_code(code, state or ""))
        _validate_oidc_access(user)
    except (OIDCAuthError, OIDCConfigError) as exc:
        st.query_params.clear()
        st.error(str(exc))
        return

    _set_auth_session(user)
    st.query_params.clear()
    st.rerun()


def _render_oidc_sign_in(app_name: str) -> None:
    if not _oidc_ready():
        _render_oidc_setup_message()

    _handle_oidc_callback()
    _render_auth_panel(app_name, f"Sign in with {_oidc_provider_name()} to continue.")

    try:
        authorization_url = _oidc_authorization_url()
    except (OIDCAuthError, OIDCConfigError) as exc:
        st.error(str(exc))
        st.stop()

    st.markdown(
        (
            f'<a class="auth-sso-button" href="{html.escape(authorization_url)}" '
            f'target="_self">Sign in with {html.escape(_oidc_provider_name())}</a>'
        ),
        unsafe_allow_html=True,
    )
    st.stop()


def _render_sign_in_form() -> None:
    with st.form(key="auth_sign_in_form"):
        st.markdown('<label class="auth-input-label">Email address</label>', unsafe_allow_html=True)
        email = st.text_input("", placeholder="you@example.com", label_visibility="collapsed")
        
        st.markdown('<label class="auth-input-label">Password</label>', unsafe_allow_html=True)
        password = st.text_input("", type="password", placeholder="Enter your password", label_visibility="collapsed")
        
        # Checkbox and forgot password row
        col1, col2 = st.columns([1, 1])
        with col1:
            remember = st.checkbox("Keep me signed in")
        with col2:
            st.markdown(
                '<div style="text-align: right;"><a href="#" class="auth-forgot">Forgot password?</a></div>',
                unsafe_allow_html=True
            )
        
        submitted = st.form_submit_button("Sign in →", use_container_width=True)

    if submitted:
        try:
            user = _sign_in(email.strip(), password)
        except (FirebaseAuthError, FirebaseConfigError) as exc:
            st.error(str(exc))
        else:
            _set_auth_session(user)
            st.rerun()


def _render_create_account_form() -> None:
    with st.form(key="auth_create_form"):
        st.markdown('<label class="auth-input-label">Display name</label>', unsafe_allow_html=True)
        display_name = st.text_input("", placeholder="Your name", label_visibility="collapsed")
        
        st.markdown('<label class="auth-input-label">Email address</label>', unsafe_allow_html=True)
        email = st.text_input("", placeholder="you@example.com", label_visibility="collapsed")
        
        st.markdown('<label class="auth-input-label">Password</label>', unsafe_allow_html=True)
        password = st.text_input("", type="password", placeholder="Create a password", label_visibility="collapsed")
        
        st.markdown('<label class="auth-input-label">Confirm password</label>', unsafe_allow_html=True)
        confirm_password = st.text_input("", type="password", placeholder="Confirm your password", label_visibility="collapsed")
        
        submitted = st.form_submit_button("Create account →", use_container_width=True)

    if submitted:
        if len(password) < 8:
            st.error("Password must be at least 8 characters.")
            return
        if password != confirm_password:
            st.error("Passwords do not match.")
            return

        try:
            user = _create_account(email.strip(), password, display_name.strip())
        except (FirebaseAuthError, FirebaseConfigError) as exc:
            st.error(str(exc))
        else:
            _set_auth_session(user)
            st.rerun()

def _render_reset_password_form() -> None:
    with st.form(key="auth_reset_form"):
        st.markdown('<p style="color: #666; font-size: 14px; margin-bottom: 16px;">Enter your email address and we\'ll send you a link to reset your password.</p>', unsafe_allow_html=True)
        st.markdown('<label class="auth-input-label">Email address</label>', unsafe_allow_html=True)
        email = st.text_input("", placeholder="you@example.com", label_visibility="collapsed")
        submitted = st.form_submit_button("Send reset link →", use_container_width=True)

    if submitted:
        try:
            _send_password_reset(email.strip())
        except (FirebaseAuthError, FirebaseConfigError) as exc:
            st.error(str(exc))
        else:
            st.success("Password reset email sent.")




def _render_social_auth_buttons(label: str) -> None:
    st.markdown(
        f'''
        <div class="auth-divider"><span>{html.escape(label)}</span></div>
        <button class="auth-social-btn" disabled>
            <svg width="20" height="20" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
            Continue with Google
        </button>
        <button class="auth-social-btn" disabled>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="#333"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg>
            Continue with GitHub
        </button>
        <button class="auth-social-btn" disabled>
            <svg width="20" height="20" viewBox="0 0 21 21"><path fill="#f25022" d="M1 1h9v9H1z"/><path fill="#00a4ef" d="M1 11h9v9H1z"/><path fill="#7fba00" d="M11 1h9v9h-9z"/><path fill="#ffb900" d="M11 11h9v9h-9z"/></svg>
            Continue with Microsoft
        </button>
        <div class="auth-footer">
            <span class="auth-footer-icon">🛡️</span>
            Protected by Firebase Authentication
        </div>
        ''',
        unsafe_allow_html=True,
    )


def require_login(app_name: str = "SNTI AI Assistant") -> dict[str, str]:
    if st.query_params.get("logout") == "1":
        _clear_auth_session()
        st.query_params.clear()
        st.rerun()

    current_user = get_current_user()
    if current_user:
        return current_user

    _render_auth_styles()

    if _auth_provider() in {"oidc", "sso", "azure", "okta"}:
        _render_oidc_sign_in(app_name)

    if not _firebase_api_key():
        _render_firebase_setup_message()

    _handle_social_oauth_callback()

    _render_auth_panel(app_name, "")

    sign_in_tab, create_tab, reset_tab = st.tabs(
        ["Sign in", "Create account", "Reset password"]
    )

    with sign_in_tab:
        _render_sign_in_form()
        _render_social_auth_buttons("or continue with")

    with create_tab:
        _render_create_account_form()
        _render_social_auth_buttons("or continue with")

    with reset_tab:
        _render_reset_password_form()
    
    # Close the auth-right div
    st.markdown("</div></div>", unsafe_allow_html=True)

    st.stop()


def logout_link(label: str = "Logout") -> str:
    return f'<a href="?logout=1" title="{label}" class="tda-icon-btn">{label}</a>'
