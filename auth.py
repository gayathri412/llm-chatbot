import base64
import hashlib
import hmac
import secrets as pysecrets

import streamlit as st


HASH_ALGORITHM = "pbkdf2_sha256"
DEFAULT_ITERATIONS = 600_000


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

    users = st.secrets.get("auth", {}).get("users", {})

    st.markdown(
        """
        <style>
        #MainMenu, footer, header { visibility: hidden; }
        .stApp { background: #0a0a0a; color: #f0f0f0; }
        [data-testid="block-container"] {
            max-width: 460px;
            padding-top: 12vh;
        }
        .auth-panel {
            border: 1px solid #2a2a2a;
            border-radius: 12px;
            background: #141414;
            padding: 28px;
            box-shadow: 0 18px 50px rgba(0, 0, 0, 0.35);
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
            color: #888;
            margin: 0;
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

    st.markdown(
        f"""
        <div class="auth-panel">
            <div class="auth-brand">SNTI AI</div>
            <h1>{app_name}</h1>
            <p>Sign in to continue.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not users:
        st.error("No users found. Add users in .streamlit/secrets.toml")
        st.stop()

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", use_container_width=True)

    if submitted:
        user_config = users.get(username)

        if user_config and verify_password(password, user_config.get("password_hash", "")):
            st.session_state.authenticated = True
            st.session_state.auth_user = username
            st.session_state.auth_name = user_config.get("name", username)
            st.rerun()

        st.error("Invalid username or password.")

    st.stop()


def logout_link(label: str = "Logout") -> str:
    return f'<a href="?logout=1" title="{label}" class="tda-icon-btn">Logout</a>'


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate a password hash.")
    parser.add_argument("password", help="Password to hash")
    args = parser.parse_args()
    print(hash_password(args.password))
