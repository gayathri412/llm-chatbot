import base64
import hashlib
import hmac
import secrets as pysecrets
from pathlib import Path

import streamlit as st


HASH_ALGORITHM = "pbkdf2_sha256"
DEFAULT_ITERATIONS = 600_000
SECRETS_PATH = Path(__file__).resolve().parent / ".streamlit" / "secrets.toml"


def hash_password(password: str, *, iterations: int = DEFAULT_ITERATIONS) -> str:
    salt = pysecrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    salt_b64 = base64.b64encode(salt).decode("ascii")
    digest_b64 = base64.b64encode(digest).decode("ascii")
    return f"{HASH_ALGORITHM}${iterations}${salt_b64}${digest_b64}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt_b64, expected_b64 = stored_hash.split("$", 3)
        if algorithm != HASH_ALGORITHM:
            return False

        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected = base64.b64decode(expected_b64.encode("ascii"))
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations),
        )
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def _toml_quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _read_local_users() -> dict:
    users = {}
    current_user = None

    try:
        lines = SECRETS_PATH.read_text(encoding="utf-8").splitlines()
    except Exception:
        return {}

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("[auth.users.") and line.endswith("]"):
            current_user = line.removeprefix("[auth.users.").removesuffix("]")
            users[current_user] = {}
            continue

        if current_user and "=" in line:
            key, value = line.split("=", 1)
            users[current_user][key.strip()] = value.strip().strip('"').strip("'")

    return users


def _save_local_user(username: str, name: str, password: str) -> None:
    SECRETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    password_hash = hash_password(password)
    content = (
        f"[auth.users.{username}]\n"
        f'name = "{_toml_quote(name)}"\n'
        f'password_hash = "{password_hash}"\n'
    )
    SECRETS_PATH.write_text(content, encoding="utf-8")


def _get_users() -> dict:
    try:
        auth_config = st.secrets.get("auth", {})
        users = auth_config.get("users", {})
        if users:
            return users
    except Exception:
        pass

    return _read_local_users()


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


def _valid_username(username: str) -> bool:
    return username.replace("_", "").replace("-", "").isalnum()


def _render_first_user_setup(app_name: str) -> None:
    _render_auth_panel(
        "Set Up Your Account",
        f"Create the first sign-in for {app_name}. No default username or password is used.",
    )

    with st.form("first_user_setup_form"):
        name = st.text_input("Display name", placeholder="Your name")
        username = st.text_input("Username", placeholder="Choose a username")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Create account", use_container_width=True)

    if submitted:
        username = username.strip()
        name = name.strip() or username

        if not username:
            st.error("Please choose a username.")
        elif not _valid_username(username):
            st.error("Use only letters, numbers, hyphens, and underscores in the username.")
        elif len(password) < 8:
            st.error("Password must be at least 8 characters.")
        elif password != confirm_password:
            st.error("Passwords do not match.")
        else:
            try:
                _save_local_user(username, name, password)
            except Exception as exc:
                st.error(f"Could not save account setup: {exc}")
            else:
                st.success("Account created. Please sign in.")
                st.rerun()

    st.info("Your password is stored locally as a salted hash, not as plain text.")
    st.stop()


def require_login(app_name: str = "SNTI AI Assistant") -> dict[str, str]:
    if st.query_params.get("logout") == "1":
        st.session_state.authenticated = False
        st.session_state.auth_user = None
        st.session_state.auth_name = None
        st.query_params.clear()
        st.rerun()

    if st.session_state.get("authenticated"):
        return {
            "username": st.session_state.get("auth_user", ""),
            "name": st.session_state.get("auth_name", ""),
        }

    users = _get_users()
    _render_auth_styles()

    if not users:
        _render_first_user_setup(app_name)

    _render_auth_panel(app_name, "Sign in with the account created for this workspace.")

    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", use_container_width=True)

    if submitted:
        username = username.strip()
        user_config = users.get(username)

        if user_config and verify_password(password, user_config.get("password_hash", "")):
            st.session_state.authenticated = True
            st.session_state.auth_user = username
            st.session_state.auth_name = user_config.get("name", username)
            st.rerun()

        st.error("That username or password does not match. Please try again.")

    st.stop()


def logout_link(label: str = "Logout") -> str:
    return f'<a href="?logout=1" title="{label}" class="tda-icon-btn">{label}</a>'


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate a password hash.")
    parser.add_argument("password", help="Password to hash")
    args = parser.parse_args()
    print(hash_password(args.password))
