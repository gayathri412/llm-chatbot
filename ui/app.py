import sys
import os
import io
import math
import requests
import base64

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
from PIL import Image, ImageEnhance, ImageDraw
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from auth import require_login
from ui.analysis import render_charts_page
from data.context import fetch_context
from app.access_control import build_access_policy
from app.config import get_settings
from app.orchestrator import answer_query as orchestrator_answer_query
from app.appwrite_storage import AppwriteStorageError
from app.firebase_storage import FirebaseStorageError
from app.upload_storage import UploadStorageError, storage_backend, upload_streamlit_file


st.set_page_config(page_title="SNTI AI Assistant", page_icon="🤖", layout="wide")

current_user = require_login("SNTI AI Assistant")
auth_user_id = current_user.get("user_id") or current_user.get("username", "anonymous")
current_access_policy = build_access_policy(current_user, get_settings())


def answer_query(query, model_choice="Llama", **kwargs):
    kwargs.setdefault("user_id", auth_user_id)
    kwargs.setdefault("user_context", current_user)
    return orchestrator_answer_query(query, model_choice, **kwargs)


model_choice = st.sidebar.selectbox(
    "Choose Model",
    ["Llama", "gpt-4o-mini", "gpt-4o"],
    key="model_selector",
)

page = st.sidebar.selectbox(
    "Choose Page",
    ["Home", "Charts"],
    key="main_page_selector",
)

if page == "Home":
    st.markdown("<br>", unsafe_allow_html=True)

elif page == "Charts":
    render_charts_page(model_choice, answer_query)



def save_upload_to_firebase(uploaded_file, area: str) -> dict | None:
    if not uploaded_file:
        return None

    file_key = (
        getattr(uploaded_file, "file_id", None)
        or f"{uploaded_file.name}:{getattr(uploaded_file, 'size', '')}"
    )
    backend = storage_backend()
    session_key = f"upload_storage:{backend}:{area}:{file_key}"

    if session_key in st.session_state:
        stored = st.session_state[session_key]
        if stored.get("uri"):
            st.caption(f"Saved to {stored.get('backend', backend).title()} Storage: `{stored['uri']}`")
            return stored
        return None

    try:
        stored = upload_streamlit_file(uploaded_file, user_id=auth_user_id, area=area)
    except (AppwriteStorageError, FirebaseStorageError, UploadStorageError) as exc:
        st.session_state[session_key] = {"error": str(exc)}
        st.warning(f"{backend.title()} Storage upload skipped: {exc}")
        return None
    except Exception as exc:
        st.session_state[session_key] = {"error": str(exc)}
        st.warning(f"{backend.title()} Storage upload failed: {exc}")
        return None

    st.session_state[session_key] = stored
    st.caption(f"Saved to {stored.get('backend', backend).title()} Storage: `{stored['uri']}`")
    return stored



# ---------- GLOBAL ----------
if "history" not in st.session_state:
    st.session_state.history = []

if "global_history" not in st.session_state:
    st.session_state.global_history = []

# ---------- PREMIUM TDA-STYLE UI ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

* { font-family: 'Inter', sans-serif; box-sizing: border-box; }

/* Hide default Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }

/* Aggressively hide native Streamlit sidebar and its toggle */
section[data-testid="stSidebar"],
[data-testid="stSidebar"],
[data-testid="collapsedControl"],
button[kind="header"],
.css-1lcbmhc, .css-17ziqus, .css-1d391kg {
    display: none !important;
    width: 0 !important;
    visibility: hidden !important;
}

/* Hide the top nav emoji-button row we injected */
[data-testid="stHorizontalBlock"]:first-of-type { display: none !important; }

/* ── FILE UPLOADER — overlaid on the + button in bottom toolbar ── */
[data-testid="stFileUploader"] {
    position: fixed !important;
    bottom: 12px !important;
    left: min(928px, calc(100vw - 190px)) !important;
    right: auto !important;
    z-index: 1103 !important;
    width: 28px !important;
    height: 26px !important;
}
/* Keep the section visible but transparent so it stays clickable */
[data-testid="stFileUploader"] section {
    border: none !important;
    background: transparent !important;
    padding: 0 !important;
    min-height: unset !important;
    width: 28px !important;
    height: 26px !important;
}
[data-testid="stFileUploaderDropzoneInstructions"],
[data-testid="stFileUploader"] span,
[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] label {
    display: none !important;
}
/* Dropzone — transparent overlay that IS clickable */
[data-testid="stFileUploaderDropzone"] {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    min-height: 26px !important;
    width: 28px !important;
    height: 26px !important;
    cursor: pointer !important;
    opacity: 0 !important;   /* invisible but fully clickable */
}
/* Only show the "Browse files" button — style it as a 📎 icon */
[data-testid="stFileUploader"] button {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 28px !important;
    height: 26px !important;
    border-radius: 8px !important;
    background: transparent !important;
    border: none !important;
    font-size: 0px !important;          /* hide button text */
    color: transparent !important;
    cursor: pointer !important;
    position: relative !important;
    transition: background 0.2s !important;
    opacity: 0 !important;
}
/* Inject a 📎 emoji via pseudo-element */
[data-testid="stFileUploader"] button::before {
    content: '📎' !important;
    font-size: 0 !important;
    color: #555 !important;
    display: block !important;
}
[data-testid="stFileUploader"] button:hover {
    background: transparent !important;
}
[data-testid="stFileUploader"] button:hover::before {
    color: #003087 !important;
}
/* Uploaded filename pill — shows above the input bar */
[data-testid="stFileUploaderFile"] {
    position: fixed !important;
    bottom: 110px !important;
    right: 80px !important;
    background: #e8f0fe !important;
    border-radius: 20px !important;
    padding: 4px 12px !important;
    font-size: 12px !important;
    color: #003087 !important;
    font-weight: 500 !important;
    z-index: 100 !important;
    border: 1px solid #b3d0f0 !important;
    max-width: 220px !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    white-space: nowrap !important;
}
/* Delete (×) button on the file pill */
[data-testid="stFileUploaderDeleteBtn"] button {
    font-size: 12px !important;
    color: #003087 !important;
    background: transparent !important;
    border: none !important;
    padding: 0 0 0 4px !important;
    cursor: pointer !important;
}

/* ══════════════════════════════════════════════
   🌑  DARK THEME  —  SNTI AI
   ══════════════════════════════════════════════ */

/* CSS Variables — swap these to change the whole theme */
:root {
    --bg-base:      #0a0a0a;   /* page background          */
    --bg-surface:   #141414;   /* header / sidebar         */
    --bg-card:      #1c1c1c;   /* cards / input box        */
    --bg-hover:     #252525;   /* hover state              */
    --border:       #2a2a2a;   /* borders                  */
    --accent:       #00c2ff;   /* cyan-blue accent         */
    --accent-dark:  #0077b6;   /* darker accent            */
    --text-primary: #f0f0f0;   /* main text                */
    --text-muted:   #888;      /* secondary text           */
    --text-dim:     #555;      /* dim icons                */
    --glow:         rgba(0, 194, 255, 0.15);
}

/* Full page background */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="block-container"] {
    background: var(--bg-base) !important;
    color: var(--text-primary) !important;
}

/* ── TOP HEADER BAR ── */
.tda-header {
    position: fixed; top: 0; left: 0; right: 0; z-index: 9999;
    height: 58px;
    background: var(--bg-surface);
    border-bottom: 1px solid var(--border);
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 20px;
    box-shadow: 0 2px 16px rgba(0,0,0,0.5);
}
.tda-header-left { display: flex; align-items: center; gap: 14px; }
.tda-header-left .hamburger { font-size: 20px; color: var(--text-muted); cursor: pointer; }
.tda-header-left .chat-icon  { font-size: 20px; color: var(--text-muted); cursor: pointer; }
.tda-logo-text {
    font-size: 17px; font-weight: 700; color: var(--accent);
    letter-spacing: 0.5px;
}
.tda-logo-text span { color: #ff4d6d; }
.tda-header-center {
    position: absolute; left: 50%; transform: translateX(-50%);
    display: flex; align-items: center;
}
.tda-header-center .center-logo {
    font-size: 15px; font-weight: 700; color: var(--accent);
    border: 2px solid var(--accent); padding: 3px 10px; border-radius: 4px;
    letter-spacing: 1px;
    box-shadow: 0 0 10px var(--glow);
}
.tda-header-center .center-sub {
    font-size: 8px; color: var(--accent); letter-spacing: 2px;
    text-align: center; display: block; opacity: 0.7;
}
.tda-header-right { display: flex; align-items: center; gap: 10px; }
.tda-badge {
    background: linear-gradient(135deg, #0077b6, #00c2ff);
    color: #000; font-size: 11px; font-weight: 700;
    padding: 3px 10px; border-radius: 12px; letter-spacing: 0.5px;
}
.tda-icon-btn {
    width: 34px; height: 34px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; cursor: pointer; color: var(--text-muted);
    transition: background 0.2s;
}
.tda-icon-btn:hover { background: var(--bg-hover); color: var(--accent); }
.tda-avatar {
    width: 34px; height: 34px; border-radius: 50%;
    background: linear-gradient(135deg, #0077b6, #00c2ff);
    display: flex; align-items: center; justify-content: center;
    color: #000; font-weight: 700; font-size: 13px;
    box-shadow: 0 0 10px var(--glow);
}

/* ── LEFT ICON SIDEBAR ── */
.tda-sidebar {
    position: fixed; left: 0; top: 58px; bottom: 0; width: 54px;
    background: var(--bg-surface);
    border-right: 1px solid var(--border);
    display: flex; flex-direction: column;
    align-items: center; padding: 16px 0; gap: 6px;
    z-index: 999;
}
.nav-icon, a.nav-icon {
    width: 40px; height: 40px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px; cursor: pointer; color: var(--text-dim);
    transition: all 0.2s; text-decoration: none;
    background: transparent;
}
.nav-icon:hover, a.nav-icon:hover {
    background: var(--bg-hover);
    color: var(--accent);
    box-shadow: 0 0 8px var(--glow);
    text-decoration: none;
}
.nav-icon.active, a.nav-icon.active { background: var(--accent) !important; color: #000 !important; }

.st-key-page_navigation {
    position: fixed;
    left: 0;
    top: 58px;
    bottom: 0;
    width: 54px;
    z-index: 1002;
    padding-top: 16px;
}
.st-key-page_navigation [role="radiogroup"] {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
}
.st-key-page_navigation label {
    width: 40px !important;
    height: 40px !important;
    border-radius: 10px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0 !important;
    cursor: pointer !important;
}
.st-key-page_navigation label > div:first-child { display: none !important; }
.st-key-page_navigation label p {
    font-size: 18px !important;
    line-height: 1 !important;
}
.st-key-page_navigation label:hover {
    background: var(--bg-hover) !important;
    box-shadow: 0 0 8px var(--glow);
}

/* ── WELCOME CARD ── */
.welcome-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 18px 22px;
    margin-bottom: 20px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.4);
    max-width: 800px;
}
.welcome-card .bot-name {
    font-size: 15px; font-weight: 700; color: var(--accent);
    display: flex; align-items: center; gap: 8px; margin-bottom: 8px;
}
.welcome-card p { color: var(--text-muted); font-size: 14px; line-height: 1.6; margin: 0; }
.welcome-card .show-more {
    color: var(--accent); font-size: 13px; cursor: pointer;
    text-decoration: underline; margin-top: 6px; display: inline-block;
}

/* ── CHAT MESSAGES ── */
.chat-wrap { max-width: 800px; }
.chat-bottom-spacer { height: 96px; }

/* Dark chat bubbles */
[data-testid="stChatMessage"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    color: var(--text-primary) !important;
}

/* ── BOTTOM INPUT BAR (stChatInput) — sits ABOVE the toolbar ── */
[data-testid="stChatInput"] {
    position: fixed !important; bottom: 9px !important;
    left: 54px !important; right: 0 !important;
    background: var(--bg-surface) !important;
    padding: 1px 32px 1px !important;
    border-top: none !important;
    z-index: 1000;
}
[data-testid="stChatInput"] > div {
    max-width: 1000px;
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px;
    box-shadow: 0 0 12px rgba(0,0,0,0.4);
    min-height: 30px !important;
    padding-left: 0 !important;
    padding-right: 4px !important;
    position: relative !important;
}
[data-testid="stChatInput"] > div:focus-within {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--glow) !important;
}
[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color: var(--text-primary) !important;
    caret-color: var(--accent) !important;
    min-height: 22px !important;
    max-height: 58px !important;
    padding-top: 2px !important;
    padding-bottom: 2px !important;
    padding-right: 158px !important;
    font-size: 14px !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: var(--text-dim) !important;
}
/* Send arrow button inside chat input */
[data-testid="stChatInput"] button {
    background: linear-gradient(135deg, #0077b6, #00c2ff) !important;
    border-radius: 9px !important;
    color: #000 !important;
    width: 30px !important;
    height: 30px !important;
    min-height: 30px !important;
}

/* ── SELECTBOX / DROPDOWNS ── */
[data-testid="stSelectbox"] > div > div {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
    border-radius: 10px !important;
}

/* ── STREAMLIT BUTTONS ── */
.stButton button {
    border-radius: 10px;
    border: 1px solid var(--border);
    background: var(--bg-card);
    color: var(--text-primary);
    transition: all 0.2s;
}
.stButton button:hover {
    background: var(--bg-hover);
    border-color: var(--accent);
    color: var(--accent);
    box-shadow: 0 0 8px var(--glow);
}

/* ── TEXT / MARKDOWN ── */
.stMarkdown, .stMarkdown p, .stMarkdown li,
h1, h2, h3, h4, h5, label, .stTextInput input, .stTextArea textarea {
    color: var(--text-primary) !important;
}
.stTextInput input, .stTextArea textarea {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--glow) !important;
}

/* ── DATAFRAME / TABLES ── */
[data-testid="stDataFrame"],
.stDataFrame { background: var(--bg-card) !important; }

/* ── FILE UPLOADER BUTTON (dark pill style) ── */
[data-testid="stFileUploader"] button::before { color: var(--accent) !important; }
[data-testid="stFileUploader"] button:hover { background: var(--bg-hover) !important; }

/* ── UPLOADED FILE PILL (dark) ── */
[data-testid="stFileUploaderFile"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--accent) !important;
    color: var(--accent) !important;
}

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg-base); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }

/* Push page content above pinned input */
.main .block-container { padding-bottom: 112px !important; padding-top: 10px !important; }

/* ── BOTTOM TOOLBAR STRIP ── */
.snti-toolbar {
    display: none !important;
}
.t-plus {
    width: 32px; height: 32px; border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    color: var(--text-muted); font-size: 20px; font-weight: 300;
    cursor: pointer; transition: all 0.2s;
    border: 1px solid var(--border); background: var(--bg-card);
    flex-shrink: 0;
}
.t-plus:hover { background: var(--bg-hover); color: var(--accent); border-color: var(--accent); }
.t-model {
    display: flex; align-items: center; gap: 6px;
    color: var(--text-muted); font-size: 13px; font-weight: 500;
    padding: 5px 10px; border-radius: 8px; cursor: pointer;
    transition: all 0.2s; user-select: none;
}
.t-model:hover { background: var(--bg-hover); color: var(--text-primary); }
.t-model .t-chevron { font-size: 9px; opacity: 0.6; }
.t-sep { width: 1px; height: 18px; background: var(--border); margin: 0 2px; }
.t-spacer { flex: 1; }
.t-plan {
    display: flex; align-items: center; gap: 6px;
    background: linear-gradient(135deg, #0077b6, #00c2ff);
    color: #000; font-size: 13px; font-weight: 700;
    padding: 6px 16px; border-radius: 20px;
    cursor: pointer; transition: all 0.2s;
    white-space: nowrap;
}
.t-plan:hover { opacity: 0.85; transform: scale(1.02); }

/* Model selectbox — overlaid on .t-model area, transparent */
[data-testid="stSelectbox"] {
    position: fixed !important;
    bottom: 12px !important;
    left: min(966px, calc(100vw - 152px)) !important;
    right: auto !important;
    z-index: 1102 !important;
    width: 78px !important;
    opacity: 0 !important;     /* invisible but clickable */
    height: 26px !important;
}
[data-testid="stSelectbox"] > div {
    height: 26px !important;
}

/* Visible inline controls inside the chat input */
.chat-inline-control {
    position: fixed;
    bottom: 12px;
    z-index: 1101;
    height: 26px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 7px;
    border: none;
    background: var(--bg-card);
    box-shadow: 0 0 0 2px var(--bg-card);
    color: var(--text-muted);
    font-size: 13px;
    pointer-events: none;
}
.chat-inline-folder {
    left: min(928px, calc(100vw - 190px));
    width: 28px;
    font-size: 13px;
}
.chat-inline-model {
    left: min(966px, calc(100vw - 152px));
    width: 78px;
    gap: 4px;
}
.chat-inline-model strong {
    color: var(--text-primary);
    font-size: 11px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# ---------- URL QUERY PARAMS & SESSION ----------
PAGES = {
    "Chat": {"title": "New Chat", "icon": "💬"},
    "Search": {"title": "Search", "icon": "🔍"},
    "Charts": {"title": "Charts", "icon": "📊"},
    "BigData": {"title": "Big Data", "icon": "🗄️"},
    "Images": {"title": "Images", "icon": "🖼️"},
    "Apps": {"title": "Apps", "icon": "📱"},
    "Research": {"title": "Research", "icon": "🧠"},
    "Codex": {"title": "Codex", "icon": "💻"},
    "GPTs": {"title": "GPTs", "icon": "🤖"},
}

query_page = st.query_params.get("page")
if query_page in PAGES:
    st.session_state.page = query_page
elif "page" not in st.session_state or st.session_state.page not in PAGES:
    st.session_state.page = "Chat"

page_options = list(PAGES)
selected_page = st.radio(
    "Navigation",
    page_options,
    index=page_options.index(st.session_state.page),
    format_func=lambda page_name: PAGES[page_name]["icon"],
    horizontal=False,
    label_visibility="collapsed",
    key="page_navigation",
)
st.session_state.page = selected_page

current_page = st.session_state.page


def get_active(page):
    return "active" if current_page == page else ""


def nav_link(page):
    item = PAGES[page]
    return (
        f'<span '
        f'class="nav-icon {get_active(page)}" '
        f'title="{item["title"]}" aria-label="{item["title"]}">'
        f'{item["icon"]}</span>'
    )

# ---------- HEADER HTML ----------
st.markdown(f"""
<!-- TOP HEADER -->
<div class="tda-header">
  <div class="tda-header-left">
    <span class="hamburger">☰</span>
    <span class="chat-icon">💬</span>
    <span class="tda-logo-text"><span>SNTI</span> AI</span>
  </div>
  <div class="tda-header-center">
    <div style="text-align:center">
      <div class="center-logo">SNTI AI</div>
      <div class="center-sub">DIGITAL ASSISTANT</div>
    </div>
  </div>
  <div class="tda-header-right">
    <span style="font-size:12px;color:#666;">GPT</span>
    <span class="tda-badge">Gemini</span>
    <div class="tda-icon-btn">🔖</div>
    <div class="tda-icon-btn">🔔</div>
    <div class="tda-avatar">S</div>
  </div>
</div>

<!-- LEFT ICON SIDEBAR -->
<div class="tda-sidebar">
</div>

""", unsafe_allow_html=True)

# ---------- SESSION ----------
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}

if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

# ---------- NAV STATE ----------
# The HTML sidebar icons above route by query parameter (?page=...).
# Model selector pinned to header area
model_choice = st.selectbox("Model", ["Auto", "Llama", "Gemini"], index=1, label_visibility="collapsed",
                             key="model_select")
st.markdown(
    f"""
    <div class="chat-inline-control chat-inline-folder" title="Upload files">&#128193;</div>
    <div class="chat-inline-control chat-inline-model" title="Switch model">
      <strong>{model_choice}</strong><span>▾</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- PAGE ROUTING ----------
page = st.session_state.page

# =========================================
# 💬 CHAT PAGE
# =========================================
if page == "Chat":

    # ---------- INIT ----------
    if "chats" not in st.session_state:
        st.session_state.chats = {"New Chat": []}

    if "current_chat" not in st.session_state:
        st.session_state.current_chat = "New Chat"

    chat_history = st.session_state.chats[st.session_state.current_chat]

    # Default values (Chat settings UI removed)
    temperature = 0.2
    show_context = False

    # ---------- FILE UPLOAD — embedded in bottom bar as 📎 icon ----------
    uploaded_file = st.file_uploader(
        "📎",
        type=["txt", "pdf", "docx"],
        label_visibility="collapsed",
        key="chat_file_uploader"
    )

    file_text = ""
    if uploaded_file:
        save_upload_to_firebase(uploaded_file, "chat")
        fname = uploaded_file.name.lower()

        if fname.endswith(".txt"):
            file_text = uploaded_file.read().decode("utf-8", errors="ignore")

        elif fname.endswith(".pdf"):
            import pdfplumber
            with pdfplumber.open(uploaded_file) as pdf:
                for p in pdf.pages:
                    file_text += p.extract_text() or ""

        elif fname.endswith(".docx"):
            try:
                from docx import Document
                doc = Document(uploaded_file)
                file_text = "\n".join([para.text for para in doc.paragraphs])
            except ImportError:
                st.error("Install python-docx: pip install python-docx")

        file_text = file_text[:5000]
        if file_text.strip():
            st.toast(f"✅ {uploaded_file.name} ready", icon="📎")
        else:
            st.warning(f"⚠️ Could not extract text from {uploaded_file.name}")

    # ---------- WELCOME CARD (shown on fresh chat) ----------
    if not chat_history:
        st.markdown(
            f"""
            <div class="welcome-card">
              <div class="bot-name">🤖 &nbsp; SNTI Digital Assistant</div>
              <p>Hello! Welcome to <strong>SNTI AI</strong> — your intelligent digital assistant.<br>
              I'm here to help you with research, data analysis, coding, image generation and more.<br>
              <span class="show-more">Tell me what you need →</span></p>
            </div>
            """,
            unsafe_allow_html=True
        )

    # ---------- DISPLAY ----------
    for turn in chat_history:
        if isinstance(turn, dict):
            q = turn.get("user", "")
            r = turn.get("bot", "")
            trace = turn.get("trace")
        else:
            q, r = turn
            trace = None

        st.chat_message("user").write(q)
        with st.chat_message("assistant"):
            st.write(r)
            if show_context and trace:
                with st.expander("Context and trace", expanded=False):
                    st.write(
                        {
                            "used_context_count": trace.get("used_context_count", 0),
                            "bq_hits": trace.get("bq_hits", 0),
                            "json_hits": trace.get("json_hits", 0),
                            "cache_hit": trace.get("cache_hit", False),
                            "tool": trace.get("tool", "none"),
                            "temperature": trace.get("temperature", temperature),
                            "pii_redacted": trace.get("pii_redacted", False),
                        }
                    )
                    sources = trace.get("context_sources", [])
                    if sources:
                        st.dataframe(sources, use_container_width=True)
                    else:
                        st.info("No retrieved context was used.")
    st.markdown('<div class="chat-bottom-spacer"></div>', unsafe_allow_html=True)
    # ---------- INPUT ----------
    user_input = st.chat_input("Ask anything...", key="main_chat")

    if user_input:
        st.chat_message("user").write(user_input)

        with st.spinner("Thinking..."):
            # 👉 PASS FILE CONTENT + USER QUESTION IF BOTH EXIST
            if file_text:
                combined_query = f"{user_input}\n\nFile content:\n{file_text}"
                result = answer_query(
                    combined_query,
                    model_choice,
                    include_trace=show_context,
                    temperature=temperature,
                    user_id=auth_user_id,
                )
            else:
                result = answer_query(
                    user_input,
                    model_choice,
                    include_trace=show_context,
                    temperature=temperature,
                    user_id=auth_user_id,
                )

        if isinstance(result, dict):
            response = result["answer"]
            trace = result.get("trace")
        else:
            response = result
            trace = None

        with st.chat_message("assistant"):
            st.write(response)
            if show_context and trace:
                with st.expander("Context and trace", expanded=False):
                    st.write(
                        {
                            "used_context_count": trace.get("used_context_count", 0),
                            "bq_hits": trace.get("bq_hits", 0),
                            "json_hits": trace.get("json_hits", 0),
                            "cache_hit": trace.get("cache_hit", False),
                            "tool": trace.get("tool", "none"),
                            "temperature": trace.get("temperature", temperature),
                            "pii_redacted": trace.get("pii_redacted", False),
                        }
                    )
                    sources = trace.get("context_sources", [])
                    if sources:
                        st.dataframe(sources, use_container_width=True)
                    else:
                        st.info("No retrieved context was used.")

        # store in chat
        chat_history.append({"user": user_input, "bot": response, "trace": trace})

        # ---------- GLOBAL MEMORY ----------
        if "global_history" not in st.session_state:
            st.session_state.global_history = []

        st.session_state.global_history.append(("user", user_input))
        st.session_state.global_history.append(("assistant", response))
# =========================================
# 🔍 SEARCH PAGE
# =========================================
elif page == "Search":
    st.title("🔍 Smart Search")

    query = st.text_input("Search anything...")

    if query:
        with st.spinner("Searching..."):
            response = answer_query(
                f"Give a clear, structured answer with points for: {query}",
                model_choice
            )

        st.write(response)

# =========================================
# 📊 CHARTS PAGE
# =========================================
elif page == "Charts":
    st.title("📊 AI Data Analytics + Prediction")

    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    from sklearn.linear_model import LinearRegression
    import pdfplumber
    import io

    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    file = st.file_uploader(
        "📂 Upload CSV or PDF",
        type=["csv", "pdf"]
    )

    if file:
        save_upload_to_firebase(file, "charts")
        st.success(f"Uploaded: {file.name}")

        styles = getSampleStyleSheet()

        # ================= CSV =================
        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
            df = df.loc[:, ~df.columns.duplicated()]
            summary = df.describe(include='all').to_string()

            # Create tabs for organized sections
            tab1, tab2, tab3, tab4, tab5 = st.tabs(["📄 Data", "📊 Graphs", "📈 Analysis", "🔮 Prediction", "📥 Download"])

            with tab1:
                st.write("### Data Preview")
                st.dataframe(df.head(20))
                st.write(f"**Shape:** {df.shape[0]} rows × {df.shape[1]} columns")
                st.write("### Statistical Summary")
                st.dataframe(df.describe())

            with tab2:
                st.write("### Graphs & Visualizations")
                cols = df.columns.tolist()
                
                col1, col2 = st.columns(2)
                with col1:
                    x_default = cols[0] if len(cols) > 0 else None
                    x_col = st.selectbox("X-axis", cols, index=0, key="graph_x")
                with col2:
                    y_default = cols[1] if len(cols) > 1 else cols[0]
                    y_index = 1 if len(cols) > 1 else 0
                    y_col = st.selectbox("Y-axis", cols, index=y_index, key="graph_y")

                if x_col != y_col:
                    df[y_col] = pd.to_numeric(df[y_col], errors='coerce')
                    chart_data = df[[x_col, y_col]].dropna()

                    if not chart_data.empty:
                        chart_type = st.selectbox(
                            "Chart Type",
                            ["Line", "Bar", "Scatter", "Histogram", "Pie", "Area"],
                            key="chart_type"
                        )

                        fig, ax = plt.subplots(figsize=(10, 6))

                        if chart_type == "Line":
                            ax.plot(chart_data[x_col], chart_data[y_col], marker='o', linewidth=2)
                            ax.set_xlabel(x_col)
                            ax.set_ylabel(y_col)
                            ax.set_title(f"{y_col} vs {x_col} - Line Chart")
                            st.pyplot(fig)

                        elif chart_type == "Bar":
                            ax.bar(chart_data[x_col], chart_data[y_col])
                            ax.set_xlabel(x_col)
                            ax.set_ylabel(y_col)
                            ax.set_title(f"{y_col} vs {x_col} - Bar Chart")
                            st.pyplot(fig)

                        elif chart_type == "Area":
                            ax.fill_between(chart_data[x_col], chart_data[y_col], alpha=0.6)
                            ax.set_xlabel(x_col)
                            ax.set_ylabel(y_col)
                            ax.set_title(f"{y_col} vs {x_col} - Area Chart")
                            st.pyplot(fig)

                        elif chart_type == "Scatter":
                            ax.scatter(chart_data[x_col], chart_data[y_col], s=50, alpha=0.7)
                            ax.set_xlabel(x_col)
                            ax.set_ylabel(y_col)
                            ax.set_title(f"{y_col} vs {x_col} - Scatter Plot")
                            st.pyplot(fig)

                        elif chart_type == "Histogram":
                            ax.hist(chart_data[y_col], bins=20, edgecolor='black', alpha=0.7)
                            ax.set_xlabel(y_col)
                            ax.set_ylabel("Frequency")
                            ax.set_title(f"Distribution of {y_col}")
                            st.pyplot(fig)

                        elif chart_type == "Pie":
                            pie_data = chart_data.groupby(x_col)[y_col].sum().reset_index()
                            fig, ax = plt.subplots(figsize=(8, 8))
                            ax.pie(pie_data[y_col], labels=pie_data[x_col], autopct='%1.1f%%', startangle=90)
                            ax.set_title(f"{y_col} by {x_col} - Pie Chart")
                            st.pyplot(fig)
                    else:
                        st.warning("No numeric data available for the selected columns")
                else:
                    st.info("Please select different columns for X and Y axes")

            with tab3:
                st.write("### AI Data Analysis")
                if st.button("🤖 Generate Analysis", key="analysis_btn"):
                    with st.spinner("Analyzing data..."):
                        analysis = answer_query(
                            f"Analyze this dataset in detail. Provide insights on trends, patterns, correlations, and key statistics:\n{summary}",
                            model_choice
                        )
                        st.session_state.analysis_result = analysis
                
                if 'analysis_result' in st.session_state:
                    st.write(st.session_state.analysis_result)

            with tab4:
                st.write("### Future Prediction")
                pred_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
                
                if len(pred_cols) > 0:
                    pred_col = st.selectbox("Select column to predict", pred_cols, key="pred_col")
                    
                    if st.button("🔮 Generate Prediction", key="pred_btn"):
                        with st.spinner("Training model and predicting..."):
                            chart_data = df[[pred_col]].dropna().reset_index(drop=True)
                            
                            if len(chart_data) > 1:
                                X = np.arange(len(chart_data)).reshape(-1, 1)
                                y = chart_data[pred_col].values

                                model = LinearRegression()
                                model.fit(X, y)

                                # Predict next 10 steps
                                future_steps = 10
                                future = np.arange(len(X), len(X) + future_steps).reshape(-1, 1)
                                pred = model.predict(future)

                                # Create prediction dataframe
                                pred_df = pd.DataFrame({
                                    "Step": list(range(len(y) + len(pred))),
                                    "Type": ["Historical"] * len(y) + ["Predicted"] * len(pred),
                                    pred_col: np.concatenate([y, pred])
                                })

                                st.write("#### Prediction Results")
                                st.dataframe(pred_df.tail(future_steps))

                                # Plot prediction
                                fig, ax = plt.subplots(figsize=(12, 6))
                                ax.plot(pred_df[pred_df["Type"] == "Historical"]["Step"], 
                                       pred_df[pred_df["Type"] == "Historical"][pred_col], 
                                       label="Historical", marker='o', linewidth=2)
                                ax.plot(pred_df[pred_df["Type"] == "Predicted"]["Step"], 
                                       pred_df[pred_df["Type"] == "Predicted"][pred_col], 
                                       label="Predicted", marker='x', linestyle='--', linewidth=2, color='red')
                                ax.set_xlabel("Step")
                                ax.set_ylabel(pred_col)
                                ax.set_title(f"{pred_col} - Historical vs Predicted")
                                ax.legend()
                                ax.grid(True, alpha=0.3)
                                st.pyplot(fig)

                                # Store for download
                                st.session_state.prediction_result = pred_df.to_string()
                                st.session_state.prediction_plot = fig
                            else:
                                st.error("Not enough data points for prediction")
                else:
                    st.warning("No numeric columns available for prediction")

            with tab5:
                st.write("### Download Complete Report")
                
                # Generate explanation if not exists
                if st.button("📋 Generate Report", key="report_btn"):
                    with st.spinner("Generating comprehensive report..."):
                        explanation = answer_query(f"Explain this dataset:\n{summary}", model_choice)
                        st.session_state.explanation = explanation
                        
                        analysis = answer_query(f"Analyze this dataset:\n{summary}", model_choice)
                        st.session_state.analysis_result = analysis

                # Create comprehensive PDF
                if st.button("📥 Download PDF Report", key="download_btn"):
                    buffer = io.BytesIO()
                    doc = SimpleDocTemplate(buffer, pagesize=(612, 792))
                    
                    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                    styles = getSampleStyleSheet()
                    
                    # Custom style for better wrapping
                    body_style = ParagraphStyle(
                        'BodyText',
                        parent=styles['Normal'],
                        fontSize=10,
                        leading=14,
                        spaceAfter=12
                    )

                    content = [
                        Paragraph("<b>Data Analysis Report</b>", styles["Title"]),
                        Spacer(1, 20),
                        Paragraph(f"<b>File:</b> {file.name}", styles["Normal"]),
                        Paragraph(f"<b>Rows:</b> {df.shape[0]} | <b>Columns:</b> {df.shape[1]}", styles["Normal"]),
                        Spacer(1, 20),
                    ]

                    # Add Explanation
                    if 'explanation' in st.session_state:
                        content.append(Paragraph("<b>Data Explanation</b>", styles["Heading2"]))
                        content.append(Paragraph(st.session_state.explanation.replace('\n', '<br/>'), body_style))
                        content.append(Spacer(1, 12))

                    # Add Analysis
                    if 'analysis_result' in st.session_state:
                        content.append(Paragraph("<b>Analysis</b>", styles["Heading2"]))
                        content.append(Paragraph(st.session_state.analysis_result.replace('\n', '<br/>'), body_style))
                        content.append(Spacer(1, 12))

                    # Add Prediction
                    if 'prediction_result' in st.session_state:
                        content.append(Paragraph("<b>Prediction</b>", styles["Heading2"]))
                        content.append(Paragraph(st.session_state.prediction_result.replace('\n', '<br/>'), body_style))

                    doc.build(content)

                    st.download_button(
                        "⬇️ Click to Download",
                        buffer.getvalue(),
                        f"{file.name}_analysis_report.pdf",
                        "application/pdf",
                        key="final_download"
                    )

        # ================= PDF =================
        elif file.name.endswith(".pdf"):
            text = ""

            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""

            st.text_area("Content", text[:2000])

            explanation = answer_query(
                f"Explain this document:\n{text[:2000]}",
                model_choice
            )
            st.write("### 🤖 Explanation")
            st.write(explanation)

            analysis = answer_query(
                f"Analyze this document:\n{text[:2000]}",
                model_choice
            )
            st.write("### 📊 Analysis")
            st.write(analysis)

            prediction = answer_query(
                f"Predict outcomes:\n{text[:2000]}",
                model_choice
            )
            st.write("### 🔮 Prediction")
            st.write(prediction)

            report = f"""
            Explanation:
            {explanation}

            Analysis:
            {analysis}

            Prediction:
            {prediction}
            """

            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer)

            content = [
                Paragraph("PDF Report", styles["Title"]),
                Spacer(1, 12),
                Paragraph(report, styles["Normal"])
            ]

            doc.build(content)

            st.download_button(
                "📥 Download Report",
                buffer.getvalue(),
                "document_report.pdf",
                "application/pdf"
            )

        # ================= FOLLOW-UP =================
        st.write("### 💬 Ask More")

        follow_up = st.text_input("Ask about the file")

        if follow_up:
            context = ""

            if file.name.endswith(".csv"):
                context = df.describe(include='all').to_string()
            elif file.name.endswith(".pdf"):
                context = text[:2000]

            reply = answer_query(
                f"Context:\n{context}\n\nQuestion:\n{follow_up}",
                model_choice
            )

            st.write(reply)

# =========================================
# �️ BIG DATA PAGE
# =========================================
elif page == "BigData":
    st.title("🗄️ Big Data Query & Analytics")

    import pandas as pd
    import io
    from prompts.compose import build_bigdata_analysis_prompt, build_sql_explanation_prompt

    # Try to import BigQuery client
    try:
        from data.bq_client import BigQueryClient, BQ_AVAILABLE
    except ImportError:
        BQ_AVAILABLE = False
        BigQueryClient = None

    # Tabs for Big Data sections
    bdtab1, bdtab2, bdtab3 = st.tabs(["🔍 SQL Query", "📤 Upload & Query", "📊 BigQuery Connect"])

    with bdtab1:
        st.write("### Write SQL Query")
        st.info("Write SQL queries to analyze your data. Works with uploaded datasets or BigQuery.")

        sql_query = st.text_area("SQL Query", 
            placeholder="SELECT * FROM my_table LIMIT 10",
            height=150
        )

        if st.button("▶️ Run Query", key="run_sql"):
            if sql_query.strip():
                with st.spinner("Executing query..."):
                    # For demo, use a sample dataframe
                    # In production, this would connect to BigQuery or database
                    try:
                        # Try to use pandasql if available
                        try:
                            from pandasql import sqldf
                            pysqldf = lambda q: sqldf(q, globals())
                            
                            # Check if we have a uploaded dataset
                            if 'uploaded_df' in st.session_state:
                                result_df = pysqldf(sql_query)
                                st.dataframe(result_df)
                                st.session_state.last_query_result = result_df
                            else:
                                st.info("Upload a CSV first in the 'Upload & Query' tab to query it with SQL")
                        except ImportError:
                            st.warning("Install pandasql for SQL querying: pip install pandasql")
                    except Exception as e:
                        st.error(f"Query error: {e}")

        # AI Explain Query
        if sql_query.strip() and st.button("🤖 Explain This Query"):
            from llm.client import chat_completion
            messages = build_sql_explanation_prompt(sql_query)
            explanation = chat_completion(messages, model_choice)
            st.write("#### Query Explanation")
            st.write(explanation)

    with bdtab2:
        st.write("### Upload Data & Query")

        uploaded_file = st.file_uploader("Upload CSV or JSON", type=["csv", "json"])

        if uploaded_file:
            save_upload_to_firebase(uploaded_file, "bigdata")
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
                st.session_state.uploaded_df = df
                st.success(f"Loaded {len(df)} rows")

                # Data preview
                st.write("#### Data Preview")
                st.dataframe(df.head(10))

                # Schema info
                st.write("#### Schema")
                schema_info = pd.DataFrame({
                    'Column': df.columns,
                    'Type': df.dtypes.astype(str),
                    'Non-Null': df.count(),
                    'Null': df.isnull().sum()
                })
                st.dataframe(schema_info)

                # Quick stats
                st.write("#### Quick Statistics")
                st.dataframe(df.describe())

            elif uploaded_file.name.endswith('.json'):
                import json
                data = json.load(uploaded_file)
                if isinstance(data, list):
                    df = pd.DataFrame(data)
                    st.session_state.uploaded_df = df
                    st.success(f"Loaded {len(df)} rows from JSON")
                    st.dataframe(df.head(10))

        # Query Builder
        if 'uploaded_df' in st.session_state:
            st.write("### Query Builder")
            df = st.session_state.uploaded_df

            col1, col2 = st.columns(2)
            with col1:
                filter_col = st.selectbox("Filter Column", ["None"] + list(df.columns))
            with col2:
                if filter_col != "None":
                    filter_val = st.text_input("Filter Value")

            if st.button("🔍 Apply Filter"):
                if filter_col != "None" and filter_val:
                    filtered_df = df[df[filter_col].astype(str).str.contains(filter_val, case=False, na=False)]
                    st.dataframe(filtered_df)
                    st.session_state.filtered_result = filtered_df

            # AI Analysis
            st.write("### AI Data Analysis")
            if st.button("🤖 Analyze Dataset"):
                with st.spinner("Analyzing..."):
                    from llm.client import chat_completion
                    summary = df.describe(include='all').to_string()
                    analysis = answer_query(f"Analyze this dataset in detail:\n{summary}", model_choice)
                    st.write(analysis)

    with bdtab3:
        st.write("### BigQuery Connection")

        if not BQ_AVAILABLE:
            st.error("BigQuery client not available. Install with: `pip install google-cloud-bigquery`")
        else:
            st.success("BigQuery client available")

            project_id = st.text_input("GCP Project ID", placeholder="my-project-123")

            if st.button("🔗 Connect to BigQuery"):
                try:
                    client = BigQueryClient(
                        project_id if project_id else None,
                        access_policy=current_access_policy,
                    )
                    st.session_state.bq_client = client
                    st.success(f"Connected to project: {client.project_id}")
                    if current_access_policy.restricted:
                        st.info("Your account is limited to approved context sources.")
                except Exception as e:
                    st.error(f"Connection failed: {e}")

            if 'bq_client' in st.session_state:
                client = st.session_state.bq_client

                # List tables
                st.write("#### Available Tables")
                dataset = st.text_input("Dataset Name", value="analytics")
                if st.button("📋 List Tables"):
                    try:
                        tables = client.list_tables(dataset)
                        st.write(tables)
                    except Exception as e:
                        st.error(f"Error: {e}")

                # Run BigQuery SQL
                st.write("#### Run BigQuery Query")
                bq_query = st.text_area("Query", 
                    f"SELECT * FROM `{client.project_id}.{dataset}.chat_context_docs` LIMIT 10",
                    height=100
                )
                if st.button("▶️ Execute"):
                    try:
                        result_df = client.execute_query(bq_query)
                        st.dataframe(result_df)

                        # AI Analysis of results
                        if st.button("🤖 Analyze Results"):
                            with st.spinner("Analyzing..."):
                                from llm.client import chat_completion
                                results_summary = result_df.to_string()
                                messages = build_bigdata_analysis_prompt("Analyze these results", bq_query, results_summary)
                                analysis = chat_completion(messages, model_choice)
                                st.write(analysis)
                    except Exception as e:
                        st.error(f"Query error: {e}")

# =========================================
# �🖼️ IMAGES PAGE
# =========================================
elif page == "Images":
    st.title("🖼️ Image AI Studio")

    # ── imports ──────────────────────────────────────────────
    import io, math, os, requests
    from PIL import Image, ImageEnhance, ImageDraw
    from dotenv import load_dotenv

    load_dotenv()

    OCR_AVAILABLE = False
    try:
        import pytesseract
        import platform
        if platform.system() == "Windows":
            pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        else:
            pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
        OCR_AVAILABLE = True   
    except Exception as e:
        st.warning(f"OCR import error: {e}")
        OCR_AVAILABLE = False

    # ── Pollinations.ai config (100% free, no API key) ───────
    POLLINATIONS_MODELS = {
        "⚡ FLUX Schnell (Fastest)":  "flux",
        "🏆 FLUX Dev    (Best)":      "flux-realism",
        "🎨 Turbo       (Creative)":  "turbo",
    }

    # ── helper: generate image via Pollinations.ai ────────────
    def generate_image(prompt: str, model: str = "flux",
                       width: int = 512, height: int = 512,
                       seed: int = None) -> Image.Image:
        encoded = requests.utils.quote(prompt)
        url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?model={model}&width={width}&height={height}&nologo=true"
        )
        if seed is not None:
            url += f"&seed={seed}"

        resp = requests.get(url, timeout=120)
        if resp.status_code != 200:
            raise Exception(f"Pollinations error {resp.status_code}: {resp.text[:200]}")
        return Image.open(io.BytesIO(resp.content)).convert("RGB")

    # ── helper: PIL → PNG bytes ───────────────────────────────
    def pil_to_bytes(img: Image.Image) -> bytes:
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="PNG")
        return buf.getvalue()

    # ── helper: dynamic image grid with download buttons ─────
    def render_image_grid(images: list, captions: list = None):
        n = len(images)
        if n == 0:
            return
        cols_count = min(n, 4)
        rows = math.ceil(n / cols_count)

        for row in range(rows):
            cols = st.columns(cols_count)
            for col_idx in range(cols_count):
                img_idx = row * cols_count + col_idx
                if img_idx >= n:
                    break
                img     = images[img_idx]
                caption = captions[img_idx] if captions else f"Image {img_idx + 1}"
                with cols[col_idx]:
                    st.image(img, caption=caption, use_column_width=True)
                    st.download_button(
                        label="⬇️ Download",
                        data=pil_to_bytes(img),
                        file_name=f"image_{img_idx + 1}.png",
                        mime="image/png",
                        key=f"dl_{row}_{col_idx}_{img_idx}"
                    )

    # ── TABS ─────────────────────────────────────────────────
    tab_gen, tab_var, tab_edit, tab_preview, tab_ocr, tab_enhance = st.tabs([
        "🎨 Generate",
        "🔁 Variations",
        "✏️ Inpaint / Edit",
        "📷 Preview",
        "🧾 OCR",
        "✨ Enhance",
    ])

    # ═══════════════════════════════════════════════════════════
    # 🎨 TAB 1 — GENERATE
    # ═══════════════════════════════════════════════════════════
    with tab_gen:
        st.subheader("Generate Images from Text")
        st.caption("✅ Powered by Pollinations.ai — 100% free, no API key required")

        model_label = st.selectbox(
            "🤖 Choose Model",
            list(POLLINATIONS_MODELS.keys()),
            help="FLUX Schnell = fastest | FLUX Realism = photorealistic | Turbo = creative"
        )
        model_id = POLLINATIONS_MODELS[model_label]
        st.caption(f"Model: `{model_id}`")

        prompt     = st.text_area("📝 Prompt", placeholder="A futuristic city at sunset, oil painting style…")
        neg_prompt = st.text_input("🚫 Negative Prompt (optional)", placeholder="blurry, bad quality, ugly…")

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            num_images = st.slider("Number of images", 1, 4, 1, key="gen_n")
        with col_b:
            size_choice = st.selectbox("Size", ["512×512", "768×768", "1024×1024", "512×768"], key="gen_size")
        with col_c:
            use_random_seed = st.checkbox("Random seed", value=True, key="gen_seed")

        st.info("💡 Tip: Use 1 image at a time to avoid rate limits on the free tier.")
        w, h = map(int, size_choice.replace("×", "x").split("x"))

        if st.button("🚀 Generate", key="btn_gen"):
            if not prompt.strip():
                st.warning("Please enter a prompt.")
            else:
                generated = []
                progress  = st.progress(0, text="Starting…")

                for i in range(num_images):
                    progress.progress(
                        int((i / num_images) * 100),
                        text=f"Generating image {i+1} of {num_images}…"
                    )
                    try:
                        full_prompt = prompt
                        if neg_prompt.strip():
                            full_prompt += f", avoid {neg_prompt}"

                        seed = None if use_random_seed else 42 + i
                        img = generate_image(full_prompt, model_id, w, h, seed)
                        generated.append(img)
                        import time
                        time.sleep(3)

                    except Exception as e:
                        st.error(f"Image {i+1} failed: {e}")

                progress.progress(100, text="Done!")

                if generated:
                    st.success(f"✅ {len(generated)} image(s) generated!")
                    captions = [f"#{i+1} • {model_label.split('(')[0].strip()}" for i in range(len(generated))]
                    render_image_grid(generated, captions)

    # ═══════════════════════════════════════════════════════════
    # 🔁 TAB 2 — VARIATIONS
    # ═══════════════════════════════════════════════════════════
    with tab_var:
        st.subheader("Image Variations")
        st.caption("Upload an image, describe it, and generate similar variations.")

        var_model_label = st.selectbox("🤖 Model", list(POLLINATIONS_MODELS.keys()), key="var_model")
        var_model_id    = POLLINATIONS_MODELS[var_model_label]

        var_file   = st.file_uploader("Upload source image", type=["png", "jpg", "jpeg"], key="var_up")
        var_prompt = st.text_input(
            "📝 Describe the image (used as base prompt)",
            placeholder="A portrait of a woman in blue…",
            key="var_prompt"
        )

        col_v1, col_v2 = st.columns(2)
        with col_v1:
            var_n = st.slider("Number of variations", 1, 4, 2, key="var_n")
        with col_v2:
            var_size = st.selectbox("Size", ["512×512", "768×768", "1024×1024"], key="var_size")

        vw, vh = map(int, var_size.replace("×", "x").split("x"))

        if var_file:
            save_upload_to_firebase(var_file, "images-variations")
            src_img = Image.open(var_file)
            st.image(src_img, caption="Source image", width=300)

            if st.button("🔁 Generate Variations", key="btn_var"):
                if not var_prompt.strip():
                    st.warning("Please describe the image to guide variations.")
                else:
                    variations = []
                    progress   = st.progress(0, text="Starting…")

                    for i in range(var_n):
                        progress.progress(
                            int((i / var_n) * 100),
                            text=f"Generating variation {i+1} of {var_n}…"
                        )
                        try:
                            varied = f"{var_prompt}, variation {i+1}, different angle, different lighting"
                            img    = generate_image(varied, var_model_id, vw, vh, seed=i * 10)
                            variations.append(img)
                        except Exception as e:
                            st.error(f"Variation {i+1} failed: {e}")

                    progress.progress(100, text="Done!")

                    if variations:
                        st.success(f"✅ {len(variations)} variation(s) ready!")
                        captions = [f"Variation {i+1}" for i in range(len(variations))]
                        render_image_grid(variations, captions)

    # ═══════════════════════════════════════════════════════════
    # ✏️ TAB 3 — INPAINT / EDIT
    # ═══════════════════════════════════════════════════════════
    with tab_edit:
        st.subheader("Inpaint / Edit")
        st.caption("Describe what you want and generate edited versions based on your prompt.")

        edit_model_label = st.selectbox("🤖 Model", list(POLLINATIONS_MODELS.keys()), key="edit_model")
        edit_model_id    = POLLINATIONS_MODELS[edit_model_label]

        edit_file   = st.file_uploader("Upload image to edit", type=["png", "jpg", "jpeg"], key="edit_up")
        edit_prompt = st.text_area(
            "✏️ Edit prompt",
            placeholder="Same scene but at night with neon lights…",
            key="edit_prompt"
        )

        col_e1, col_e2 = st.columns(2)
        with col_e1:
            edit_n    = st.slider("Number of outputs", 1, 4, 1, key="edit_n")
        with col_e2:
            edit_size = st.selectbox("Size", ["512×512", "768×768", "1024×1024"], key="edit_size")

        ew, eh = map(int, edit_size.replace("×", "x").split("x"))

        if edit_file:
            save_upload_to_firebase(edit_file, "images-edit")
            src_img = Image.open(edit_file).convert("RGB")
            st.image(src_img, caption="Image to edit", width=300)

            if st.button("✏️ Apply Edit", key="btn_edit"):
                if not edit_prompt.strip():
                    st.warning("Please enter an edit prompt.")
                else:
                    edits    = []
                    progress = st.progress(0, text="Starting…")

                    for i in range(edit_n):
                        progress.progress(
                            int((i / edit_n) * 100),
                            text=f"Generating edit {i+1} of {edit_n}…"
                        )
                        try:
                            img = generate_image(edit_prompt, edit_model_id, ew, eh, seed=i * 7)
                            edits.append(img)
                        except Exception as e:
                            st.error(f"Edit {i+1} failed: {e}")

                    progress.progress(100, text="Done!")

                    if edits:
                        st.success(f"✅ {len(edits)} edited image(s) ready!")
                        all_imgs     = [src_img] + edits
                        all_captions = ["Original"] + [f"Edit {i+1}" for i in range(len(edits))]
                        render_image_grid(all_imgs, all_captions)

    # ═══════════════════════════════════════════════════════════
    # 📷 TAB 4 — PREVIEW
    # ═══════════════════════════════════════════════════════════
    with tab_preview:
        st.subheader("Preview Uploaded Image")
        prev_file = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"], key="prev_up")

        if prev_file:
            save_upload_to_firebase(prev_file, "images-preview")
            image = Image.open(prev_file)
            st.image(image, caption="Uploaded Image")
            st.write(f"**Size:** {image.size[0]} × {image.size[1]} px")
            st.write(f"**Mode:** {image.mode}")

            if st.button("🤖 Analyze Image", key="btn_analyze"):
                with st.spinner("Analyzing with Gemini Vision…"):
                    try:
                        import google.generativeai as genai
                        import base64

                        buf = io.BytesIO()
                        image.convert("RGB").save(buf, format="JPEG")
                        buf.seek(0)
                        model_gemini = genai.GenerativeModel("gemini-2.5-flash")
                        response = model_gemini.generate_content([
                            "Analyze this image in detail. Provide: 1) Full description 2) Key objects and elements 3) Colors and mood 4) Possible meaning or use case 5) Any text visible in the image.",
                            {"mime_type": "image/jpeg", "data": buf.getvalue()}
                        ])

                        st.write("### 🤖 Gemini Vision Analysis")
                        st.write(response.text)
                    except Exception as e:
                        st.error(f"Gemini Vision failed: {e}")


            st.download_button(
                "⬇️ Download Original",
                data=pil_to_bytes(image),
                file_name="original.png",
                mime="image/png",
                key="dl_orig"
            )

    # ═══════════════════════════════════════════════════════════
    # 🧾 TAB 5 — OCR
    # ═══════════════════════════════════════════════════════════
    with tab_ocr:
        st.subheader("Extract Text from Image (OCR)")
        ocr_file = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"], key="ocr_up")

        if ocr_file:
            save_upload_to_firebase(ocr_file, "images-ocr")
            ocr_img = Image.open(ocr_file)
            st.image(ocr_img, width=300)
            
            import shutil, platform
            st.write(f"OCR_AVAILABLE: {OCR_AVAILABLE}")
            st.write(f"Tesseract binary: {shutil.which('tesseract')}")
            st.write(f"Platform: {platform.system()}")

            if st.button("🔍 Extract Text", key="btn_ocr"):
                if not OCR_AVAILABLE:
                    st.error("Tesseract OCR is not installed or not found.")
                else:
                    with st.spinner("Reading text…"):
                        text = pytesseract.image_to_string(ocr_img)
                    st.text_area("Extracted Text", text, height=200)
                    st.download_button(
                        "⬇️ Download Text",
                        data=text.encode(),
                        file_name="ocr_output.txt",
                        mime="text/plain",
                        key="dl_ocr"
                    )

    # ═══════════════════════════════════════════════════════════
    # ✨ TAB 6 — ENHANCE
    # ═══════════════════════════════════════════════════════════
    with tab_enhance:
        st.subheader("Enhance Image")
        enh_file = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"], key="enh_up")

        if enh_file:
            save_upload_to_firebase(enh_file, "images-enhance")
            enh_img    = Image.open(enh_file)
            brightness = st.slider("Brightness", 0.5, 2.0, 1.0, key="brightness")
            contrast   = st.slider("Contrast",   0.5, 2.0, 1.0, key="contrast")
            sharpness  = st.slider("Sharpness",  0.5, 3.0, 1.0, key="sharpness")

            enhanced = ImageEnhance.Brightness(enh_img).enhance(brightness)
            enhanced = ImageEnhance.Contrast(enhanced).enhance(contrast)
            enhanced = ImageEnhance.Sharpness(enhanced).enhance(sharpness)

            col_e1, col_e2 = st.columns(2)
            with col_e1:
                st.image(enh_img,  caption="Original", use_column_width=True)
            with col_e2:
                st.image(enhanced, caption="Enhanced",  use_column_width=True)

            st.download_button(
                "⬇️ Download Enhanced",
                data=pil_to_bytes(enhanced),
                file_name="enhanced.png",
                mime="image/png",
                key="dl_enh"
            )
   
# =========================================
# 📱 APPS PAGE
# =========================================
if page == "Apps":
    st.title("📱 AI Tools Hub")

    import pandas as pd
    import numpy as np
    import requests
    import re

    # ---------- SELECT APP ----------
    app = st.selectbox("Choose App", [
        "📄 PDF Analyzer",
        "📊 CSV Analyzer",
        "🧾 Resume Analyzer",
        "🔐 Password Tester",
        "💬 Writing Assistant"
    ])

    # =========================================================
    # 📄 PDF ANALYZER
    # =========================================================
    if app == "📄 PDF Analyzer":
        import pdfplumber

        file = st.file_uploader("Upload PDF", type=["pdf"])

        if file:
            save_upload_to_firebase(file, "apps-pdf")
            text = ""
            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""

            st.text_area("Preview", text[:1500])

            if st.button("Analyze PDF"):
                summary = answer_query(
                    f"Summarize and extract key points:\n{text[:2000]}",
                    model_choice
                )
                st.write(summary)

    # =========================================================
    # 📊 CSV ANALYZER
    # =========================================================
    elif app == "📊 CSV Analyzer":
        file = st.file_uploader("Upload CSV", type=["csv"])

        if file:
            save_upload_to_firebase(file, "apps-csv")
            df = pd.read_csv(file)
            st.dataframe(df.head())

            st.write("### Basic Stats")
            st.write(df.describe())

            col = st.selectbox("Select column for analysis", df.columns)

            if df[col].dtype != "object":
                st.line_chart(df[col])

    # =========================================================
    # 🧾 RESUME ANALYZER
    # =========================================================
    elif app == "🧾 Resume Analyzer":
        resume_text = st.text_area("Paste Resume Text")

        if st.button("Analyze Resume"):
            result = answer_query(
                f"Analyze this resume. Extract skills, strengths, weaknesses, and suggestions:\n{resume_text}",
                model_choice
            )
            st.write(result)

    # =========================================================
    # 🔐 PASSWORD TESTER
    # =========================================================
    elif app == "🔐 Password Tester":
        password = st.text_input("Enter Password", type="password")

        def check_strength(p):
            score = 0
            if len(p) >= 8:
                score += 1
            if re.search(r"[A-Z]", p):
                score += 1
            if re.search(r"[0-9]", p):
                score += 1
            if re.search(r"[!@#$%^&*]", p):
                score += 1
            return score

        if password:
            score = check_strength(password)

            if score <= 1:
                st.error("Weak Password")
            elif score == 2:
                st.warning("Moderate Password")
            else:
                st.success("Strong Password")

    # =========================================================
    # 💬 WRITING ASSISTANT
    # =========================================================
    elif app == "💬 Writing Assistant":
        text = st.text_area("Enter Text")

        action = st.selectbox("Choose Action", [
            "Rewrite",
            "Summarize",
            "Fix Grammar"
        ])

        if st.button("Process"):
            prompt = f"{action} this text:\n{text}"
            result = answer_query(prompt, model_choice)
            st.write(result)
# =========================================
# 🧠 RESEARCH PAGE
# =========================================
elif page == "Research":
    st.title("🧠 AI Research Assistant")

    feature = st.selectbox("Select Tool", [
        "📌 Topic Planner",
        "📚 Literature Review",
        "✍️ Paper Generator",
        "📊 Methodology Helper",
        "📖 Citation Generator"
    ])

    # =========================================================
    # 📌 TOPIC PLANNER
    # =========================================================
    if feature == "📌 Topic Planner":
        topic = st.text_input("Enter Research Topic")

        if st.button("Generate Plan"):
            response = answer_query(
                f"""
                For the topic '{topic}', generate:
                1. Subtopics
                2. Research questions
                3. Keywords
                """,
                model_choice
            )
            st.write(response)

    # =========================================================
    # 📚 LITERATURE REVIEW
    # =========================================================
    elif feature == "📚 Literature Review":
        text = st.text_area("Paste abstract or research content")

        if st.button("Generate Review"):
            if not text.strip():
                st.warning("⚠️ Please enter research content")
            else:
                with st.spinner("Analyzing research content..."):
                    response = answer_query(
                    f"""
                    You are an academic research assistant.

                    Analyze the following research content and give:

                    1. Summary
                    2. Key Findings
                    3. Research Gaps
                    4. Improvements

                    {text}
                    """,
                    model_choice
                )

            st.write("### 📚 Literature Review Output")
            st.write(response)
    # =========================================================
    # ✍️ PAPER GENERATOR
    # =========================================================
    elif feature == "✍️ Paper Generator":
        topic = st.text_input("Enter Topic")

        if st.button("Generate Paper"):
            response = answer_query(
                f"""
                Write a research paper on '{topic}' including:
                - Abstract
                - Introduction
                - Methodology
                - Conclusion
                """,
                model_choice
            )
            st.write(response)

    # =========================================================
    # 📊 METHODOLOGY HELPER
    # =========================================================
    elif feature == "📊 Methodology Helper":
        topic = st.text_input("Enter Research Topic")

        if st.button("Suggest Methodology"):
            response = answer_query(
                f"""
                Suggest a research methodology for '{topic}' including:
                - Approach (ML, rule-based, hybrid)
                - Dataset ideas
                - Evaluation metrics
                """,
                model_choice
            )
            st.write(response)

    # =========================================================
    # 📖 CITATION GENERATOR
    # =========================================================
    elif feature == "📖 Citation Generator":
        content = st.text_area("Paste content or title")

        style = st.selectbox("Select Citation Style", [
            "APA", "MLA", "IEEE"
        ])

        if st.button("Generate Citation"):
            response = answer_query(
                f"Convert this into {style} citation:\n{content}",
                model_choice
            )
            st.write(response)

# =========================================
# 💻 CODEX PAGE
# =========================================
elif page == "Codex":
    st.title("💻 AI Codex Assistant")

    tool = st.selectbox("Select Tool", [
        "🧠 Code Generator",
        "🐞 Bug Fixer",
        "📖 Code Explainer",
        "🔄 Code Converter",
        "⚡ Code Optimizer"
    ])

    # =========================================================
    # 🧠 CODE GENERATOR
    # =========================================================
    if tool == "🧠 Code Generator":
        prompt = st.text_area("Describe what you want to build")

        if st.button("Generate Code"):
            if prompt.strip():
                with st.spinner("Generating code..."):
                    response = answer_query(
                        f"""
                        Write clean and complete code for:
                        {prompt}

                        Include:
                        - Comments
                        - Proper structure
                        - Best practices
                        """,
                        model_choice
                    )
                st.code(response, language="python")
            else:
                st.warning("Please enter a prompt")

    # =========================================================
    # 🐞 BUG FIXER
    # =========================================================
    elif tool == "🐞 Bug Fixer":
        code = st.text_area("Paste your code or error")

        if st.button("Fix Bug"):
            if code.strip():
                with st.spinner("Fixing..."):
                    response = answer_query(
                        f"""
                        Fix the following code and explain the issue:

                        {code}
                        """,
                        model_choice
                    )
                st.write(response)
            else:
                st.warning("Please paste code")

    # =========================================================
    # 📖 CODE EXPLAINER
    # =========================================================
    elif tool == "📖 Code Explainer":
        code = st.text_area("Paste code to explain")

        if st.button("Explain Code"):
            if code.strip():
                with st.spinner("Explaining..."):
                    response = answer_query(
                        f"""
                        Explain this code step by step in simple terms:

                        {code}
                        """,
                        model_choice
                    )
                st.write(response)
            else:
                st.warning("Please paste code")

    # =========================================================
    # 🔄 CODE CONVERTER
    # =========================================================
    elif tool == "🔄 Code Converter":
        code = st.text_area("Paste code")
        target_lang = st.selectbox("Convert to", ["Python", "Java", "C++", "JavaScript"])

        if st.button("Convert Code"):
            if code.strip():
                with st.spinner("Converting..."):
                    response = answer_query(
                        f"""
                        Convert this code into {target_lang}:

                        {code}
                        """,
                        model_choice
                    )
                st.code(response)
            else:
                st.warning("Please paste code")

    # =========================================================
    # ⚡ CODE OPTIMIZER
    # =========================================================
    elif tool == "⚡ Code Optimizer":
        code = st.text_area("Paste code to optimize")

        if st.button("Optimize Code"):
            if code.strip():
                with st.spinner("Optimizing..."):
                    response = answer_query(
                        f"""
                        Optimize this code for:
                        - Better performance
                        - Clean structure
                        - Readability

                        {code}
                        """,
                        model_choice
                    )
                st.write(response)
            else:
                st.warning("Please paste code")

    # =========================================================
    # 💬 FOLLOW-UP CHAT
    # =========================================================
    st.write("### 💬 Ask Coding Questions")

    user_q = st.chat_input("Ask anything about coding...")

    if user_q:
        st.chat_message("user").write(user_q)

        reply = answer_query(user_q, model_choice)

        st.chat_message("assistant").write(reply)

# =========================================
# 🤖 GPTs PAGE
# =========================================
elif page == "GPTs":
    st.title("🤖 Custom GPTs")

    gpt = st.selectbox("Choose GPT", [
        "🔬 Research GPT",
        "💻 Coding GPT",
        "🔐 Cybersecurity GPT",
        "📊 Data Analyst GPT",
        "✍️ Writing GPT",
        "🎯 Interview Prep GPT"
    ])

    # ---------- SYSTEM PROMPTS ----------
    if gpt == "🔬 Research GPT":
        system_prompt = """
        You are an academic research assistant.
        Provide structured, formal, and detailed answers.
        """

    elif gpt == "💻 Coding GPT":
        system_prompt = """
        You are an expert software developer.
        Write clean, efficient, and well-commented code.
        """

    elif gpt == "🔐 Cybersecurity GPT":
        system_prompt = """
        You are a cybersecurity expert.
        Analyze threats, vulnerabilities, and suggest prevention methods.
        """

    elif gpt == "📊 Data Analyst GPT":
        system_prompt = """
        You are a data analyst.
        Provide insights, trends, and clear explanations of data.
        """

    elif gpt == "✍️ Writing GPT":
        system_prompt = """
        You are a professional writer.
        Improve clarity, grammar, and structure.
        """

    elif gpt == "🎯 Interview Prep GPT":
        system_prompt = """
        You are a technical interviewer.
        Ask questions and evaluate answers with feedback.
        """

    # ---------- CHAT HISTORY ----------
    if "gpt_history" not in st.session_state:
        st.session_state.gpt_history = []

    # ---------- DISPLAY CHAT ----------
    for role, msg in st.session_state.gpt_history:
        st.chat_message(role).write(msg)

    # ---------- INPUT ----------
    user_input = st.chat_input("Ask your GPT...")

    if user_input:
        st.session_state.gpt_history.append(("user", user_input))

        st.chat_message("user").write(user_input)

        with st.spinner("Thinking..."):
            reply = answer_query(
                system_prompt + "\nUser: " + user_input,
                model_choice
            )

        st.session_state.gpt_history.append(("assistant", reply))
        st.chat_message("assistant").write(reply)

    # ---------- CLEAR CHAT ----------
    if st.button("🗑️ Clear Chat"):
        st.session_state.gpt_history = []

