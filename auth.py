import os
from typing import Any

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


def _get_secret_value(section: str, key: str) -> str | None:
    try:
        values = st.secrets.get(section, {})
        if hasattr(values, "get"):
            return values.get(key) or None
    except Exception:
        pass
    return None


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
    }
    return messages.get(code, "Firebase could not complete this request. Please try again.")


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


def _clear_auth_session() -> None:
    for key in (
        "authenticated",
        "auth_provider",
        "auth_user",
        "auth_user_id",
        "auth_email",
        "auth_name",
        "firebase_id_token",
        "firebase_refresh_token",
    ):
        st.session_state.pop(key, None)


def _set_auth_session(user: dict[str, str]) -> None:
    st.session_state.authenticated = True
    st.session_state.auth_provider = "firebase"
    st.session_state.auth_user = user["username"]
    st.session_state.auth_user_id = user["user_id"]
    st.session_state.auth_email = user["email"]
    st.session_state.auth_name = user["name"]
    st.session_state.firebase_id_token = user["id_token"]
    st.session_state.firebase_refresh_token = user["refresh_token"]


def get_current_user() -> dict[str, str] | None:
    if not st.session_state.get("authenticated"):
        return None

    return {
        "provider": st.session_state.get("auth_provider", "firebase"),
        "user_id": st.session_state.get("auth_user_id", ""),
        "username": st.session_state.get("auth_user", ""),
        "email": st.session_state.get("auth_email", ""),
        "name": st.session_state.get("auth_name", ""),
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

    if not _firebase_api_key():
        _render_firebase_setup_message()

    _render_auth_panel(
        app_name,
        "Sign in with Firebase Authentication, or create an account for this workspace.",
    )

    sign_in_tab, create_tab, reset_tab = st.tabs(["Sign in", "Create account", "Reset password"])
    with sign_in_tab:
        _render_sign_in_form()
    with create_tab:
        _render_create_account_form()
    with reset_tab:
        _render_reset_password_form()

    st.stop()


def logout_link(label: str = "Logout") -> str:
    return f'<a href="?logout=1" title="{label}" class="tda-icon-btn">{label}</a>'
