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


def _render_auth_styles() -> None:
    st.markdown(
        """
        <style>
        #MainMenu, footer, header { visibility: hidden; }
        .stApp { background: #0a0a0a; color: #f0f0f0; }
        [data-testid="block-container"] {
            max-width: 520px;
            padding-top: 10vh;
        }
        .auth-panel {
            border: 1px solid #2a2a2a;
            border-radius: 12px;
            background: #141414;
            padding: 28px;
            box-shadow: 0 18px 50px rgba(0, 0, 0, 0.35);
            margin-bottom: 16px;
        }
        .auth-brand {
            color: #00c2ff;
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }
        .auth-panel h1 {
            color: #f0f0f0;
            font-size: 28px;
            margin: 0 0 8px;
        }
        .auth-panel p {
            color: #aaa;
            margin: 0;
            line-height: 1.5;
        }
        .stTextInput input {
            background: #1c1c1c;
            border: 1px solid #2a2a2a;
            color: #f0f0f0;
            border-radius: 10px;
        }
        .stButton button {
            background: linear-gradient(135deg, #0077b6, #00c2ff);
            border: none;
            color: #000;
            font-weight: 700;
            border-radius: 10px;
        }
        .auth-sso-button {
            display: block;
            width: 100%;
            padding: 12px 16px;
            border-radius: 10px;
            background: linear-gradient(135deg, #0077b6, #00c2ff);
            color: #000 !important;
            font-weight: 700;
            text-align: center;
            text-decoration: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_auth_panel(title: str, message: str) -> None:
    st.markdown(
        f"""
        <div class="auth-panel">
            <div class="auth-brand">SNTI AI</div>
            <h1>{title}</h1>
            <p>{message}</p>
        </div>
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
    with st.form("firebase_sign_in_form"):
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", use_container_width=True)

    if submitted:
        try:
            user = _sign_in(email.strip(), password)
        except (FirebaseAuthError, FirebaseConfigError) as exc:
            st.error(str(exc))
        else:
            _set_auth_session(user)
            st.rerun()


def _render_create_account_form() -> None:
    with st.form("firebase_create_account_form"):
        display_name = st.text_input("Display name", placeholder="Your name")
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Create account", use_container_width=True)

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
    with st.form("firebase_reset_password_form"):
        email = st.text_input("Account email", placeholder="you@example.com")
        submitted = st.form_submit_button("Send reset email", use_container_width=True)

    if submitted:
        try:
            _send_password_reset(email.strip())
        except (FirebaseAuthError, FirebaseConfigError) as exc:
            st.error(str(exc))
        else:
            st.success("Password reset email sent.")


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

    _render_auth_panel(
        app_name,
        "Sign in with Firebase Authentication, or create an account for this workspace.",
    )

    sign_in_tab, create_tab, reset_tab = st.tabs(
        ["Sign in", "Create account", "Reset password"]
    )

    with sign_in_tab:
        _render_sign_in_form()

        st.divider()
        st.write("Or continue with")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Continue with Google", use_container_width=True, key="google_sign_in"):
                st.info("Google sign-in needs OAuth setup.")

        with col2:
            if st.button("Continue with GitHub", use_container_width=True, key="github_sign_in"):
                st.info("GitHub sign-in needs OAuth setup.")

    with create_tab:
        _render_create_account_form()

        st.divider()
        st.write("Or create with")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Continue with Google", use_container_width=True, key="google_create"):
                st.info("Google sign-in needs OAuth setup.")

        with col2:
            if st.button("Continue with GitHub", use_container_width=True, key="github_create"):
                st.info("GitHub sign-in needs OAuth setup.")

    with reset_tab:
        _render_reset_password_form()

    st.stop()


def logout_link(label: str = "Logout") -> str:
    return f'<a href="?logout=1" title="{label}" class="tda-icon-btn">{label}</a>'
