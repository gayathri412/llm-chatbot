# app.py — SNTI AI Assistant
# Firebase auth + Google/GitHub/Microsoft OAuth + auto-refresh + inactivity timeout
# New in this version:
#   • JS heartbeat  — mouse/keyboard/touch/scroll events ping Python via
#                     st.query_params; pauses when tab is hidden (visibilitychange)
#   • Warning banner + modal countdown — shown IDLE_WARN_SEC before auto-logout
#   • touch_activity() wired into every login form, OAuth callbacks, and UI action
#
# Execution sequence:
#   1.  Imports & config
#   2.  Session persistence helpers
#   3.  Token refresh helpers
#   4.  Firebase email/password auth
#   5.  OAuth providers
#   6.  Inactivity tracking  (touch_activity / check_inactivity / _idle_remaining)
#   7.  JS heartbeat injector  (inject_heartbeat_js)
#   8.  Idle warning banner  (render_idle_warning)
#   9.  Login UI  (render_login)
#   10. Auth gate  (require_login)
#   11. Logout confirmation dialog
#   12. Main app
# ─────────────────────────────────────────────────────────────────────────────

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

# ─────────────────────────────────────────────────────────────────────────────
# 1. Config
# ─────────────────────────────────────────────────────────────────────────────
FIREBASE_API_KEY       = os.getenv("FIREBASE_API_KEY", "")
APP_REDIRECT_URI       = os.getenv("APP_REDIRECT_URI", "http://localhost:8501")

GOOGLE_CLIENT_ID       = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET   = os.getenv("GOOGLE_CLIENT_SECRET", "")

GITHUB_CLIENT_ID       = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET   = os.getenv("GITHUB_CLIENT_SECRET", "")

MS_CLIENT_ID           = os.getenv("MS_CLIENT_ID", "")
MS_CLIENT_SECRET       = os.getenv("MS_CLIENT_SECRET", "")
MS_TENANT              = os.getenv("MS_TENANT", "common")

SESSION_FILE           = Path(os.getenv("SESSION_FILE", ".snti_session.json"))
REFRESH_LEEWAY_SEC     = 300
INACTIVITY_TIMEOUT_MIN = int(os.getenv("INACTIVITY_TIMEOUT_MIN", "15"))
INACTIVITY_TIMEOUT_SEC = INACTIVITY_TIMEOUT_MIN * 60
# JS warns this many seconds before the hard Python timeout
IDLE_WARN_SEC          = int(os.getenv("IDLE_WARN_SEC", "120"))   # default: 2 min before
# How often the browser sends a "still alive" ping to Python
HEARTBEAT_INTERVAL_SEC = int(os.getenv("HEARTBEAT_INTERVAL_SEC", "30"))

FIREBASE_SIGNIN_URL    = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
FIREBASE_SIGNUP_URL    = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
FIREBASE_RESET_URL     = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={FIREBASE_API_KEY}"
FIREBASE_IDP_URL       = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp?key={FIREBASE_API_KEY}"
FIREBASE_REFRESH_URL   = f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_API_KEY}"

# ─────────────────────────────────────────────────────────────────────────────
# 2. Session persistence
# ─────────────────────────────────────────────────────────────────────────────
def _load_persisted() -> dict[str, Any] | None:
    if not SESSION_FILE.exists():
        return None
    try:
        return json.loads(SESSION_FILE.read_text())
    except Exception:
        return None

def _save_persisted(data: dict[str, Any]) -> None:
    try:
        SESSION_FILE.write_text(json.dumps(data))
    except Exception:
        pass

def _clear_persisted() -> None:
    try:
        SESSION_FILE.unlink(missing_ok=True)
    except Exception:
        pass

def save_session(payload: dict[str, Any]) -> None:
    expires_in = int(payload.get("expiresIn", 3600))
    record = {
        "idToken":      payload["idToken"],
        "refreshToken": payload["refreshToken"],
        "localId":      payload.get("localId") or payload.get("user_id"),
        "email":        payload.get("email", ""),
        "displayName":  payload.get("displayName", ""),
        "photoUrl":     payload.get("photoUrl", ""),
        "provider":     payload.get("providerId", "password"),
        "expiresAt":    int(time.time()) + expires_in,
    }
    st.session_state["auth"] = record
    _save_persisted(record)
    touch_activity()   # every successful auth resets the idle clock

def clear_session() -> None:
    st.session_state.pop("auth", None)
    st.session_state.pop("last_activity", None)
    st.session_state.pop("_idle_warning_shown", None)
    _clear_persisted()

def hydrate_from_disk() -> None:
    if "auth" in st.session_state:
        return
    persisted = _load_persisted()
    if persisted:
        st.session_state["auth"] = persisted

# ─────────────────────────────────────────────────────────────────────────────
# 3. Token refresh
# ─────────────────────────────────────────────────────────────────────────────
def _refresh(refresh_token: str) -> dict[str, Any]:
    r = requests.post(
        FIREBASE_REFRESH_URL,
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()

def ensure_fresh_token() -> bool:
    auth = st.session_state.get("auth")
    if not auth:
        return False
    if int(time.time()) < auth["expiresAt"] - REFRESH_LEEWAY_SEC:
        return True
    try:
        data = _refresh(auth["refreshToken"])
        auth["idToken"]      = data["id_token"]
        auth["refreshToken"] = data["refresh_token"]
        auth["expiresAt"]    = int(time.time()) + int(data["expires_in"])
        st.session_state["auth"] = auth
        _save_persisted(auth)
        return True
    except Exception:
        clear_session()
        return False

def authed_headers() -> dict[str, str]:
    if not ensure_fresh_token():
        return {}
    return {"Authorization": f"Bearer {st.session_state['auth']['idToken']}"}

# ─────────────────────────────────────────────────────────────────────────────
# 4. Firebase email/password auth
# ─────────────────────────────────────────────────────────────────────────────
def _firebase_err(r: requests.Response) -> str:
    try:
        return r.json().get("error", {}).get("message", "Unknown error")
    except Exception:
        return "Unknown error"

def email_signin(email: str, password: str) -> tuple[bool, str]:
    r = requests.post(
        FIREBASE_SIGNIN_URL,
        json={"email": email, "password": password, "returnSecureToken": True},
        timeout=10,
    )
    if r.status_code != 200:
        return False, _firebase_err(r)
    save_session(r.json())   # save_session → touch_activity internally
    return True, "Signed in"

def email_signup(email: str, password: str) -> tuple[bool, str]:
    r = requests.post(
        FIREBASE_SIGNUP_URL,
        json={"email": email, "password": password, "returnSecureToken": True},
        timeout=10,
    )
    if r.status_code != 200:
        return False, _firebase_err(r)
    save_session(r.json())
    return True, "Account created"

def password_reset(email: str) -> tuple[bool, str]:
    r = requests.post(
        FIREBASE_RESET_URL,
        json={"requestType": "PASSWORD_RESET", "email": email},
        timeout=10,
    )
    if r.status_code != 200:
        return False, _firebase_err(r)
    touch_activity()   # form submit counts as user interaction
    return True, "Password reset email sent"

# ─────────────────────────────────────────────────────────────────────────────
# 5. OAuth providers
# ─────────────────────────────────────────────────────────────────────────────
PROVIDERS = {
    "google": {
        "label": "Continue with Google",
        "auth":  "https://accounts.google.com/o/oauth2/v2/auth",
        "token": "https://oauth2.googleapis.com/token",
        "scope": "openid email profile",
        "client_id":     GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "fb_provider":   "google.com",
    },
    "github": {
        "label": "Continue with GitHub",
        "auth":  "https://github.com/login/oauth/authorize",
        "token": "https://github.com/login/oauth/access_token",
        "scope": "read:user user:email",
        "client_id":     GITHUB_CLIENT_ID,
        "client_secret": GITHUB_CLIENT_SECRET,
        "fb_provider":   "github.com",
    },
    "microsoft": {
        "label": "Continue with Microsoft",
        "auth":  f"https://login.microsoftonline.com/{MS_TENANT}/oauth2/v2.0/authorize",
        "token": f"https://login.microsoftonline.com/{MS_TENANT}/oauth2/v2.0/token",
        "scope": "openid email profile",
        "client_id":     MS_CLIENT_ID,
        "client_secret": MS_CLIENT_SECRET,
        "fb_provider":   "microsoft.com",
    },
}

def oauth_url(provider: str) -> str:
    cfg = PROVIDERS[provider]
    state = pysecrets.token_urlsafe(24)
    st.session_state[f"oauth_state_{provider}"] = state
    params = {
        "client_id":     cfg["client_id"],
        "redirect_uri":  APP_REDIRECT_URI,
        "response_type": "code",
        "scope":         cfg["scope"],
        "state":         f"{provider}:{state}",
    }
    touch_activity()   # user clicked an OAuth button
    return f"{cfg['auth']}?{urlencode(params)}"

def exchange_code(provider: str, code: str) -> str:
    cfg = PROVIDERS[provider]
    r = requests.post(
        cfg["token"],
        data={
            "client_id":     cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "code":          code,
            "redirect_uri":  APP_REDIRECT_URI,
            "grant_type":    "authorization_code",
        },
        headers={"Accept": "application/json"},
        timeout=10,
    )
    r.raise_for_status()
    body = r.json()
    return body.get("id_token") or body.get("access_token", "")

def firebase_signin_with_idp(provider: str, token: str) -> tuple[bool, str]:
    cfg = PROVIDERS[provider]
    key = "id_token" if provider in ("google", "microsoft") else "access_token"
    r = requests.post(
        FIREBASE_IDP_URL,
        json={
            "postBody":            f"{key}={token}&providerId={cfg['fb_provider']}",
            "requestUri":          APP_REDIRECT_URI,
            "returnSecureToken":   True,
            "returnIdpCredential": True,
        },
        timeout=10,
    )
    if r.status_code != 200:
        return False, _firebase_err(r)
    save_session(r.json())   # save_session → touch_activity internally
    return True, "Signed in"

def handle_oauth_callback() -> None:
    """
    Processes query params on every render.

    Two cases:
      ?_heartbeat=<epoch>   — JS heartbeat ping → touch_activity() then clear
      ?code=…&state=…       — OAuth provider redirect → exchange + sign in
    """
    qp = st.query_params

    # ── JS heartbeat ping ────────────────────────────────────────────────────
    if qp.get("_heartbeat"):
        touch_activity()
        st.query_params.clear()
        return   # heartbeat render: nothing else to process

    # ── OAuth redirect ───────────────────────────────────────────────────────
    code  = qp.get("code")
    state = qp.get("state")
    if not code or not state or ":" not in state:
        return
    provider, nonce = state.split(":", 1)
    if provider not in PROVIDERS:
        return
    if st.session_state.get(f"oauth_state_{provider}") != nonce:
        st.error("OAuth state mismatch")
        st.query_params.clear()
        return
    try:
        token = exchange_code(provider, code)
        ok, msg = firebase_signin_with_idp(provider, token)
        if not ok:
            st.error(f"{provider} sign-in failed: {msg}")
        else:
            touch_activity()   # explicit touch after successful OAuth flow
    except Exception as e:
        st.error(f"OAuth error: {e}")
    st.query_params.clear()

# ─────────────────────────────────────────────────────────────────────────────
# 6. Inactivity tracking
# ─────────────────────────────────────────────────────────────────────────────
def touch_activity() -> None:
    """
    Reset the idle timer.

    Called from:
      • save_session()              — every successful sign-in / sign-up
      • password_reset()            — password-reset form submit
      • oauth_url()                 — OAuth button click
      • firebase_signin_with_idp()  — OAuth callback completion
      • handle_oauth_callback()     — JS heartbeat ping
      • render_login() form submits — explicit call before each auth call
      • _confirm_logout() Cancel    — cancelling the dialog
      • main() sidebar/top-bar btns — opening the logout dialog
      • main() top of render loop   — catch-all for every other interaction
    """
    st.session_state["last_activity"] = int(time.time())
    st.session_state.pop("_idle_warning_shown", None)   # re-arm warning

def check_inactivity() -> bool:
    """
    Server-side hard gate.
    Returns True  → still active.
    Returns False → timed out; session cleared, _idle_logout flag set.
    """
    if "auth" not in st.session_state:
        return False
    now  = int(time.time())
    last = st.session_state.get("last_activity")
    if last is None:
        st.session_state["last_activity"] = now
        return True
    if now - last > INACTIVITY_TIMEOUT_SEC:
        clear_session()
        st.session_state["_idle_logout"] = True
        return False
    return True

def _idle_remaining() -> int:
    """Seconds until idle logout (≥ 0)."""
    last = st.session_state.get("last_activity", int(time.time()))
    return max(0, INACTIVITY_TIMEOUT_SEC - (int(time.time()) - last))

# ─────────────────────────────────────────────────────────────────────────────
# 7. JS heartbeat injector
# ─────────────────────────────────────────────────────────────────────────────
def inject_heartbeat_js() -> None:
    """
    Injects a self-contained <script> block that:

    Activity detection
      Listens for mousemove / mousedown / keydown / touchstart / scroll / wheel
      on document (passive, 2-second client-side throttle).
      Resets a JS-side lastActivity timestamp and dismisses any visible warning.

    Tab visibility
      Pauses all timers while document.hidden is true.
      On becoming visible again, resets lastActivity so the tab re-entering
      focus doesn't immediately count the hidden time as idle.

    Warning overlay (shown IDLE_WARN_SEC before timeout)
      • Amber fixed banner at top of viewport with live "X m Ys" countdown
        and an "I'm still here" button.
      • Centred modal with the same countdown, a "Stay signed in" primary
        button, and a "Sign out now" secondary that clicks the sidebar button.
      Dismissed instantly by any user input event.

    Heartbeat ping
      When the user has been active since the last ping, the script navigates
      to ?_heartbeat=<epoch> every HEARTBEAT_INTERVAL_SEC seconds.
      handle_oauth_callback() catches the param, calls touch_activity(), and
      clears the param so the URL stays clean.
      Inactive tabs are deliberately NOT pinged — Python's check_inactivity()
      will handle the hard timeout.

    Idempotency
      window.__sntiHB guards against double-injection across Streamlit reruns.
    """
    timeout_ms  = INACTIVITY_TIMEOUT_SEC * 1000
    warn_ms     = IDLE_WARN_SEC * 1000
    interval_ms = HEARTBEAT_INTERVAL_SEC * 1000

    st.markdown(f"""
<script>
(function() {{
  if (window.__sntiHB) return;
  window.__sntiHB = true;

  const TIMEOUT_MS  = {timeout_ms};
  const WARN_MS     = {warn_ms};
  const INTERVAL_MS = {interval_ms};

  let lastActivity = Date.now();
  let tabVisible   = !document.hidden;
  let lastPing     = Date.now();
  let warnVisible  = false;
  let countdownEl  = null;   // banner span
  let modalCdEl    = null;   // modal span
  let tickTimer    = null;

  // ── Utilities ────────────────────────────────────────────────────────────
  function msRemaining() {{
    return Math.max(0, TIMEOUT_MS - (Date.now() - lastActivity));
  }}

  function fmtMs(ms) {{
    const s = Math.ceil(ms / 1000);
    const m = Math.floor(s / 60);
    const r = s % 60;
    return m > 0 ? m + 'm ' + r + 's' : r + 's';
  }}

  function ping() {{
    const url = new URL(window.location.href);
    url.searchParams.set('_heartbeat', Date.now());
    window.location.href = url.toString();
  }}

  // ── Warning UI ────────────────────────────────────────────────────────────
  function showWarning() {{
    if (warnVisible) return;
    warnVisible = true;

    /* — Banner — */
    const banner = document.createElement('div');
    banner.id = 'snti-idle-banner';
    Object.assign(banner.style, {{
      position:'fixed', top:'0', left:'0', right:'0', zIndex:'99999',
      background:'#f59e0b', color:'#1c1917', padding:'10px 16px',
      display:'flex', alignItems:'center', justifyContent:'space-between',
      fontFamily:'system-ui,sans-serif', fontSize:'14px', fontWeight:'600',
      boxShadow:'0 2px 8px rgba(0,0,0,.25)',
    }});
    const bannerLeft = document.createElement('span');
    bannerLeft.innerHTML = '&#9888;&#65039; Session expiring in <span id="snti-cd"></span>';
    countdownEl = bannerLeft.querySelector('#snti-cd');

    const stayBtn = document.createElement('button');
    stayBtn.textContent = "I'm still here";
    Object.assign(stayBtn.style, {{
      background:'#1c1917', color:'#fef3c7', border:'none',
      padding:'6px 14px', borderRadius:'6px', cursor:'pointer',
      fontSize:'13px', fontWeight:'700',
    }});
    stayBtn.onclick = function() {{ dismissWarning(); ping(); }};
    banner.appendChild(bannerLeft);
    banner.appendChild(stayBtn);
    document.body.prepend(banner);

    /* — Modal — */
    const overlay = document.createElement('div');
    overlay.id = 'snti-idle-modal';
    Object.assign(overlay.style, {{
      position:'fixed', inset:'0', zIndex:'100000',
      background:'rgba(0,0,0,.55)', display:'flex',
      alignItems:'center', justifyContent:'center',
    }});

    const box = document.createElement('div');
    Object.assign(box.style, {{
      background:'#fff', borderRadius:'16px', padding:'2rem 2.5rem',
      maxWidth:'380px', width:'90%', textAlign:'center',
      boxShadow:'0 20px 60px rgba(0,0,0,.3)',
      fontFamily:'system-ui,sans-serif',
    }});
    box.innerHTML = `
      <div style="font-size:2.5rem;margin-bottom:.75rem">&#9203;</div>
      <h2 style="margin:0 0 .5rem;font-size:1.2rem;color:#0f172a">Still there?</h2>
      <p style="color:#64748b;font-size:.9rem;margin:0 0 1.25rem">
        You'll be automatically signed out in<br>
        <strong id="snti-modal-cd"
          style="color:#f59e0b;font-size:1.3rem"></strong>
      </p>
      <button id="snti-stay"
        style="background:#1e3a8a;color:#fff;border:none;padding:.65rem 1.5rem;
               borderRadius:10px;cursor:pointer;fontSize:.95rem;fontWeight:600;
               width:100%;marginBottom:.5rem">
        Stay signed in
      </button>
      <button id="snti-signout"
        style="background:transparent;color:#94a3b8;border:none;
               padding:.4rem;cursor:pointer;fontSize:.85rem;width:100%">
        Sign out now
      </button>`;
    modalCdEl = box.querySelector('#snti-modal-cd');
    box.querySelector('#snti-stay').onclick = function() {{ dismissWarning(); ping(); }};
    box.querySelector('#snti-signout').onclick = function() {{
      const lb = [...document.querySelectorAll('button')]
                   .find(b => b.textContent.trim() === 'Log out');
      if (lb) lb.click();
    }};
    overlay.appendChild(box);
    document.body.appendChild(overlay);

    tickTimer = setInterval(updateCountdown, 1000);
    updateCountdown();
  }}

  function updateCountdown() {{
    const rem   = msRemaining();
    const label = fmtMs(rem);
    if (countdownEl) countdownEl.textContent = label;
    if (modalCdEl)   modalCdEl.textContent   = label;
    if (rem <= 0) {{
      clearInterval(tickTimer);
      dismissWarning();
      ping();   // final ping — Python will expire the session on next render
    }}
  }}

  function dismissWarning() {{
    warnVisible = false;
    if (tickTimer) {{ clearInterval(tickTimer); tickTimer = null; }}
    const b = document.getElementById('snti-idle-banner');
    const m = document.getElementById('snti-idle-modal');
    if (b) b.remove();
    if (m) m.remove();
    countdownEl = null;
    modalCdEl   = null;
  }}

  // ── User activity events ──────────────────────────────────────────────────
  let throttled = false;
  function onActivity() {{
    if (!tabVisible) return;
    lastActivity = Date.now();
    if (warnVisible) dismissWarning();
    if (throttled) return;
    throttled = true;
    setTimeout(function() {{ throttled = false; }}, 2000);
  }}
  ['mousemove','mousedown','keydown','touchstart','scroll','wheel']
    .forEach(function(e) {{
      document.addEventListener(e, onActivity, {{passive:true}});
    }});

  // ── Tab visibility ────────────────────────────────────────────────────────
  document.addEventListener('visibilitychange', function() {{
    tabVisible = !document.hidden;
    if (tabVisible) {{
      // Don't penalise the user for the time the tab was hidden
      lastActivity = Date.now();
    }}
  }});

  // ── Main 1-second polling loop ────────────────────────────────────────────
  setInterval(function() {{
    if (!tabVisible) return;

    const rem = msRemaining();

    // Show warning overlay when within the warn window
    if (rem > 0 && rem <= WARN_MS) showWarning();

    // Send heartbeat only when the user has been recently active
    const sinceLastPing     = Date.now() - lastPing;
    const sinceLastActivity = Date.now() - lastActivity;
    if (sinceLastPing >= INTERVAL_MS && sinceLastActivity < INTERVAL_MS + 5000) {{
      lastPing = Date.now();
      ping();
    }}
  }}, 1000);

}})();
</script>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 8. Server-side idle warning banner (fallback for JS-blocked clients)
# ─────────────────────────────────────────────────────────────────────────────
def render_idle_warning() -> None:
    """
    Renders a Streamlit warning banner when the server-side idle clock is
    within IDLE_WARN_SEC of the hard timeout.  Acts as a fallback when the
    JS heartbeat cannot run (no-script environment, Streamlit Cloud sandbox).
    """
    rem = _idle_remaining()
    if rem > IDLE_WARN_SEC:
        return
    m     = rem // 60
    s     = rem % 60
    label = f"{m}m {s}s" if m else f"{s}s"
    st.warning(
        f"⚠️ **Inactivity warning** — you will be signed out in **{label}**. "
        "Move the mouse or press any key to stay signed in.",
    )

# ─────────────────────────────────────────────────────────────────────────────
# 9. Login UI
# ─────────────────────────────────────────────────────────────────────────────
def _inject_css() -> None:
    st.markdown("""
    <style>
      .block-container { padding-top: 2rem; max-width: 1100px; }
      .snti-hero {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
        color: #fff; padding: 3rem 2rem; border-radius: 16px; height: 100%;
      }
      .snti-hero h1 { font-size: 2.25rem; margin: 0 0 1rem; }
      .snti-hero p  { opacity: .85; line-height: 1.6; }
      .snti-card {
        background: #fff; padding: 2rem; border-radius: 16px;
        box-shadow: 0 8px 30px rgba(0,0,0,.08);
      }
      .snti-divider {
        display: flex; align-items: center; gap: .75rem;
        color: #94a3b8; font-size: .8rem; margin: 1rem 0;
      }
      .snti-divider::before, .snti-divider::after {
        content: ""; flex: 1; height: 1px; background: #e2e8f0;
      }
      .oauth-btn a {
        display: flex; align-items: center; justify-content: center; gap: .5rem;
        width: 100%; padding: .65rem 1rem; border: 1px solid #e2e8f0;
        border-radius: 10px; text-decoration: none; color: #0f172a !important;
        font-weight: 500; background: #fff; transition: all .15s;
      }
      .oauth-btn a:hover { background: #f8fafc; border-color: #cbd5e1; }
    </style>
    """, unsafe_allow_html=True)

def _oauth_button(provider: str, icon: str) -> None:
    cfg = PROVIDERS[provider]
    if not cfg["client_id"]:
        st.markdown(
            f'<div class="oauth-btn"><a style="opacity:.5;pointer-events:none">'
            f'{icon} {cfg["label"]} (not configured)</a></div>',
            unsafe_allow_html=True,
        )
        return
    url = oauth_url(provider)   # oauth_url() calls touch_activity()
    st.markdown(
        f'<div class="oauth-btn"><a href="{url}" target="_self">{icon} {cfg["label"]}</a></div>',
        unsafe_allow_html=True,
    )

def render_login() -> None:
    _inject_css()
    left, right = st.columns([1, 1], gap="large")

    with left:
        st.markdown("""
        <div class="snti-hero">
          <h1>SNTI AI Assistant</h1>
          <p>Secure, provider-agnostic sign-in. Use email or your favourite
          identity provider — your session refreshes automatically so you
          stay logged in across reloads.</p>
        </div>
        """, unsafe_allow_html=True)

    with right:
        st.markdown('<div class="snti-card">', unsafe_allow_html=True)

        _oauth_button("google",    "🟢")
        _oauth_button("github",    "⚫")
        _oauth_button("microsoft", "🔷")

        st.markdown('<div class="snti-divider">or continue with email</div>',
                    unsafe_allow_html=True)

        tab_signin, tab_signup, tab_reset = st.tabs(["Sign in", "Sign up", "Forgot password"])

        with tab_signin:
            with st.form("signin_form", clear_on_submit=False):
                email = st.text_input("Email",    key="si_email")
                pw    = st.text_input("Password", type="password", key="si_pw")
                if st.form_submit_button("Sign in", use_container_width=True, type="primary"):
                    touch_activity()   # ← form submit
                    if not email or not pw:
                        st.error("Email and password are required")
                    else:
                        ok, msg = email_signin(email, pw)
                        (st.success if ok else st.error)(msg)
                        if ok:
                            st.rerun()

        with tab_signup:
            with st.form("signup_form"):
                email = st.text_input("Email",                  key="su_email")
                pw    = st.text_input("Password (min 6 chars)", type="password", key="su_pw")
                pw2   = st.text_input("Confirm password",       type="password", key="su_pw2")
                if st.form_submit_button("Create account", use_container_width=True, type="primary"):
                    touch_activity()   # ← form submit
                    if pw != pw2:
                        st.error("Passwords do not match")
                    elif len(pw) < 6:
                        st.error("Password must be at least 6 characters")
                    else:
                        ok, msg = email_signup(email, pw)
                        (st.success if ok else st.error)(msg)
                        if ok:
                            st.rerun()

        with tab_reset:
            with st.form("reset_form"):
                email = st.text_input("Email", key="rs_email")
                if st.form_submit_button("Send reset link", use_container_width=True):
                    touch_activity()   # ← form submit
                    ok, msg = password_reset(email)
                    (st.success if ok else st.error)(msg)

        st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 10. Auth gate
# ─────────────────────────────────────────────────────────────────────────────
def require_login() -> dict[str, Any]:
    """
    Must be the first call inside main().

    Execution order
    ───────────────
    a) Restore session from disk
    b) Handle OAuth redirect OR JS heartbeat ping (both via query params)
    c) Fast-path: if auth exists, token is fresh, and session is active → return
    d) Show idle-logout banner from the previous render (if applicable)
    e) Fall through to login page + stop
    """
    hydrate_from_disk()      # a
    handle_oauth_callback()  # b

    # c — all three checks in one branch; short-circuits on the happy path
    if (
        "auth" in st.session_state
        and ensure_fresh_token()
        and check_inactivity()
    ):
        return st.session_state["auth"]

    # d — check_inactivity() may have just cleared the session and set this flag
    if st.session_state.pop("_idle_logout", False):
        st.warning(
            f"You were logged out after {INACTIVITY_TIMEOUT_MIN} minutes of inactivity."
        )

    # e — no valid session; show login and stop
    render_login()
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# 11. Logout confirmation dialog
# ─────────────────────────────────────────────────────────────────────────────
@st.dialog("Confirm logout")
def _confirm_logout() -> None:
    st.write("Are you sure you want to log out? Your saved session will be cleared.")
    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button("Yes, log out", type="primary", use_container_width=True):
            clear_session()
            st.rerun()
    with col_no:
        if st.button("Cancel", use_container_width=True):
            touch_activity()   # cancelling the dialog = user is still here
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# 12. Main app
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    st.set_page_config(page_title="SNTI AI Assistant", page_icon="🤖", layout="wide")

    if not FIREBASE_API_KEY:
        st.error("FIREBASE_API_KEY is not set. Add it to your .env file.")
        st.stop()

    # ── Step 1: Auth gate ─────────────────────────────────────────────────────
    #    Handles: disk hydration · OAuth/heartbeat callback · inactivity gate ·
    #             token refresh.  Returns auth dict or calls st.stop().
    user = require_login()

    # ── Step 2: Inject JS heartbeat ───────────────────────────────────────────
    #    Must come AFTER require_login so unauthenticated renders don't get it.
    #    Idempotent — window.__sntiHB guard prevents double-injection.
    inject_heartbeat_js()

    # ── Step 3: Touch activity — catch-all for every Streamlit render ─────────
    #    Any widget interaction that didn't call touch_activity() explicitly
    #    is captured here because Streamlit reruns on every interaction.
    touch_activity()

    # ── Step 4: Server-side idle warning banner (JS-off fallback) ─────────────
    render_idle_warning()

    # ── Step 5: Sidebar ───────────────────────────────────────────────────────
    with st.sidebar:
        if user.get("photoUrl"):
            st.image(user["photoUrl"], width=64)
        st.markdown(f"**{user.get('displayName') or user['email']}**")
        st.caption(f"Provider: `{user.get('provider', 'password')}`")

        token_rem = max(0, user["expiresAt"] - int(time.time()))
        st.caption(f"Token expires in: {token_rem // 60}m {token_rem % 60}s")

        idle_rem = _idle_remaining()
        st.caption(f"Idle timeout in: {idle_rem // 60}m {idle_rem % 60}s")

        st.divider()
        if st.button("Log out", use_container_width=True):
            touch_activity()    # opening the dialog = interaction
            _confirm_logout()

    # ── Step 6: Top bar ───────────────────────────────────────────────────────
    col_title, col_user, col_logout = st.columns([6, 2, 1])
    with col_title:
        st.title("SNTI AI Assistant")
    with col_user:
        st.markdown(f"**{user.get('displayName') or user['email']}**")
        st.caption(f"via {user.get('provider', 'password')}")
    with col_logout:
        if st.button("Log out", type="secondary", use_container_width=True, key="top_logout"):
            touch_activity()
            _confirm_logout()

    st.divider()

    # ── Step 7: App body ──────────────────────────────────────────────────────
    st.write(f"Welcome, **{user.get('displayName') or user['email']}** 👋")
    st.info("You're signed in. Tokens refresh automatically — feel free to reload.")

    # ── Place your real app widgets below this line ───────────────────────────


if __name__ == "__main__":
    main()