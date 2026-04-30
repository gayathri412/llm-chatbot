import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from data.context import fetch_context
import io, math, requests, base64
from PIL import Image, ImageEnhance, ImageDraw
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

import streamlit as st
from app.orchestrator import answer_query


st.set_page_config(page_title="SNTI AI Assistant", page_icon="🤖", layout="wide")

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
    bottom: 4px !important;
    left: 62px !important;
    right: auto !important;
    z-index: 1100 !important;
    width: 44px !important;
    height: 44px !important;
}
/* Keep the section visible but transparent so it stays clickable */
[data-testid="stFileUploader"] section {
    border: none !important;
    background: transparent !important;
    padding: 0 !important;
    min-height: unset !important;
    width: 44px !important;
    height: 44px !important;
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
    min-height: 44px !important;
    width: 44px !important;
    height: 44px !important;
    cursor: pointer !important;
    opacity: 0 !important;   /* invisible but fully clickable */
}
/* Only show the "Browse files" button — style it as a 📎 icon */
[data-testid="stFileUploader"] button {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 38px !important;
    height: 38px !important;
    border-radius: 10px !important;
    background: transparent !important;
    border: none !important;
    font-size: 0px !important;          /* hide button text */
    color: transparent !important;
    cursor: pointer !important;
    position: relative !important;
    transition: background 0.2s !important;
}
/* Inject a 📎 emoji via pseudo-element */
[data-testid="stFileUploader"] button::before {
    content: '📎' !important;
    font-size: 20px !important;
    color: #555 !important;
    display: block !important;
}
[data-testid="stFileUploader"] button:hover {
    background: #e8f0fe !important;
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
.nav-icon {
    width: 40px; height: 40px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px; cursor: pointer; color: var(--text-dim);
    transition: all 0.2s; text-decoration: none;
}
.nav-icon:hover {
    background: var(--bg-hover);
    color: var(--accent);
    box-shadow: 0 0 8px var(--glow);
}
.nav-icon.active { background: var(--accent); color: #000; }

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

/* Dark chat bubbles */
[data-testid="stChatMessage"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    color: var(--text-primary) !important;
}

/* ── BOTTOM INPUT BAR (stChatInput) — sits ABOVE the toolbar ── */
[data-testid="stChatInput"] {
    position: fixed !important; bottom: 46px !important;
    left: 54px !important; right: 0 !important;
    background: var(--bg-surface) !important;
    padding: 10px 32px 8px !important;
    border-top: none !important;
    z-index: 1000;
}
[data-testid="stChatInput"] > div {
    max-width: 800px;
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px;
    box-shadow: 0 0 12px rgba(0,0,0,0.4);
}
[data-testid="stChatInput"] > div:focus-within {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--glow) !important;
}
[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color: var(--text-primary) !important;
    caret-color: var(--accent) !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: var(--text-dim) !important;
}
/* Send arrow button inside chat input */
[data-testid="stChatInput"] button {
    background: linear-gradient(135deg, #0077b6, #00c2ff) !important;
    border-radius: 10px !important;
    color: #000 !important;
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
.main .block-container { padding-bottom: 130px !important; padding-top: 10px !important; }

/* ── BOTTOM TOOLBAR STRIP ── */
.snti-toolbar {
    position: fixed;
    bottom: 0; left: 54px; right: 0;
    height: 46px;
    background: var(--bg-surface);
    border-top: 1px solid var(--border);
    display: flex; align-items: center;
    padding: 0 20px 0 16px;
    z-index: 1001;
    gap: 8px;
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
    bottom: 5px !important;
    left: 112px !important;
    z-index: 1102 !important;
    width: 180px !important;
    opacity: 0 !important;     /* invisible but clickable */
    height: 36px !important;
}
[data-testid="stSelectbox"] > div {
    height: 36px !important;
}
</style>

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
  <div class="nav-icon" title="Chat">💬</div>
  <div class="nav-icon" title="Charts">📊</div>
  <div class="nav-icon" title="Search">🔍</div>
  <div class="nav-icon" title="Images">🖼️</div>
  <div class="nav-icon" title="Research">🧠</div>
  <div class="nav-icon" title="Codex">💻</div>
  <div class="nav-icon" title="GPTs">🤖</div>
</div>

<!-- BOTTOM TOOLBAR -->
<div class="snti-toolbar" id="snti-toolbar">
  <div class="t-plus" title="Upload file">+</div>
  <div class="t-sep"></div>
  <div class="t-model" title="Switch model" id="t-model-label">
    <span id="t-model-name">Llama</span>
    <span class="t-chevron">&#9650;</span>
  </div>
  <div class="t-spacer"></div>
  <div class="t-plan">Plan &nbsp;&#8594;</div>
</div>
""", unsafe_allow_html=True)

# ---------- SESSION ----------
if "page" not in st.session_state:
    st.session_state.page = "Chat"

if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}

if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

# ---------- NAV STATE (hidden buttons via session_state URL-style) ----------
# The HTML sidebar icons above are decorative; real nav is via these hidden vars.
# Model selector pinned to header area
model_choice = st.selectbox("Model", ["Llama", "Gemini"], label_visibility="collapsed",
                             key="model_select")

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

    # ---------- FILE UPLOAD — embedded in bottom bar as 📎 icon ----------
    uploaded_file = st.file_uploader(
        "📎",
        type=["txt", "pdf", "docx"],
        label_visibility="collapsed",
        key="chat_file_uploader"
    )

    file_text = ""
    if uploaded_file:
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
    for q, r in chat_history:
        st.chat_message("user").write(q)
        st.chat_message("assistant").write(r)
    # ---------- INPUT ----------
    user_input = st.chat_input("Ask anything...", key="main_chat")

    if user_input:
        st.chat_message("user").write(user_input)

        with st.spinner("Thinking..."):
            # 👉 PASS FILE CONTENT + USER QUESTION IF BOTH EXIST
            if file_text:
                combined_query = f"{user_input}\n\nFile content:\n{file_text}"
                response = answer_query(combined_query, model_choice)
            else:
                response = answer_query(user_input, model_choice)

        st.chat_message("assistant").write(response)

        # store in chat
        chat_history.append((user_input, response))

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
        st.success(f"Uploaded: {file.name}")

        styles = getSampleStyleSheet()

        # ================= CSV =================
        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
            df = df.loc[:, ~df.columns.duplicated()]

            st.write("### 📄 Data Preview")
            st.dataframe(df.head())

            # --------- EXPLAIN ----------
            st.write("### 🤖 Data Explanation")
            summary = df.describe(include='all').to_string()

            explanation = answer_query(
                f"Explain this dataset:\n{summary}",
                model_choice
            )
            st.write(explanation)

            # --------- SELECT ----------
            cols = df.columns.tolist()
            x_col = st.selectbox("X-axis", cols)
            y_col = st.selectbox("Y-axis", cols)

            if x_col != y_col:
                df[y_col] = pd.to_numeric(df[y_col], errors='coerce')
                chart_data = df[[x_col, y_col]].dropna()

                if not chart_data.empty:
                    st.write("### 📊 Visualization")

                    chart_type = st.selectbox(
                        "Chart Type",
                        ["Line", "Bar", "Scatter"]
                    )

                    if chart_type == "Line":
                        st.line_chart(chart_data, x=x_col, y=y_col)

                    elif chart_type == "Bar":
                        st.bar_chart(chart_data, x=x_col, y=y_col)

                    elif chart_type == "Scatter":
                        fig, ax = plt.subplots()
                        ax.scatter(chart_data[x_col], chart_data[y_col])
                        st.pyplot(fig)

                    # --------- ANALYSIS ----------
                    st.write("### 📊 Analysis")

                    analysis = answer_query(
                        f"Analyze trends:\n{summary}",
                        model_choice
                    )
                    st.write(analysis)

                    # --------- PREDICTION ----------
                    st.write("### 🔮 Prediction")

                    X = np.arange(len(chart_data)).reshape(-1, 1)
                    y = chart_data[y_col].values

                    model = LinearRegression()
                    model.fit(X, y)

                    future = np.arange(len(X), len(X)+5).reshape(-1, 1)
                    pred = model.predict(future)

                    st.write(pred)

                    pred_df = pd.DataFrame({
                        "Index": list(range(len(y) + len(pred))),
                        "Value": np.concatenate([y, pred])
                    })

                    st.line_chart(pred_df, x="Index", y="Value")

                    # --------- PDF DOWNLOAD ----------
                    report = f"""
                    Explanation:
                    {explanation}

                    Analysis:
                    {analysis}

                    Prediction:
                    {pred}
                    """

                    buffer = io.BytesIO()
                    doc = SimpleDocTemplate(buffer)

                    content = [
                        Paragraph("CSV Report", styles["Title"]),
                        Spacer(1, 12),
                        Paragraph(report, styles["Normal"])
                    ]

                    doc.build(content)

                    st.download_button(
                        "📥 Download Report",
                        buffer.getvalue(),
                        "csv_report.pdf",
                        "application/pdf"
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
# 🖼️ IMAGES PAGE
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

