import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from data.context import fetch_context
import io, math, requests, base64
from PIL import Image, ImageEnhance, ImageDraw
from openai import OpenAI
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

import streamlit as st
from app.orchestrator import answer_query


api_key = st.secrets.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

st.set_page_config(page_title="AI Assistant", page_icon="🤖", layout="wide")

# ---------- GLOBAL ----------
import streamlit as st

if "history" not in st.session_state:
    st.session_state.history = []

if "global_history" not in st.session_state:
    st.session_state.global_history = []

# ---------- UI STYLE ----------
st.markdown("""
<style>
.stButton button {border-radius: 10px;}
.stTextInput input {border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

# ---------- CONFIG ----------
st.set_page_config(page_title="SNTI Model", layout="wide")

# ---------- SESSION ----------
if "page" not in st.session_state:
    st.session_state.page = "Chat"

if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}

if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

# ---------- SIDEBAR ----------
st.sidebar.title("💬 SNTI")

if st.sidebar.button("➕ New Chat"):
    name = f"Chat {len(st.session_state.chats)+1}"
    st.session_state.chats[name] = []
    st.session_state.current_chat = name
    st.session_state.page = "Chat"

if st.sidebar.button("🔍 Search"):
    st.session_state.page = "Search"

if st.sidebar.button("📊 Charts"):
    st.session_state.page = "Charts"

if st.sidebar.button("🖼️ Images"):
    st.session_state.page = "Images"

if st.sidebar.button("📱 Apps"):
    st.session_state.page = "Apps"

if st.sidebar.button("🧠 Research"):
    st.session_state.page = "Research"

if st.sidebar.button("💻 Codex"):
    st.session_state.page = "Codex"

if st.sidebar.button("🤖 GPTs"):
    st.session_state.page = "GPTs"

col1, col2 = st.columns([6,1])

with col2:
    model_choice = st.selectbox("Model", ["Llama", "Gemini"])

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

    # ---------- FILE UPLOAD (ADD HERE) ----------
    uploaded_file = st.file_uploader("Upload a file", type=["txt", "pdf"])

    file_text = ""
    if uploaded_file:
        if uploaded_file.type == "text/plain":
            file_text = uploaded_file.read().decode("utf-8")

        elif uploaded_file.type == "application/pdf":
            import pdfplumber
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    file_text += page.extract_text() or ""
        
        file_text = file_text[:5000]

        st.success("File uploaded successfully ✅")

    # ---------- HOME SCREEN ----------
    if not chat_history:
        st.markdown(
            f"""
            <div style='text-align:center; margin-top:150px;'>
                <h1 style='font-size:40px;'>🤖 {model_choice}</h1>
                <p style='font-size:18px; color:#888;'>What can I help you with?</p>
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
            # 👉 PASS FILE CONTENT IF EXISTS
            if file_text:
                response = answer_query(file_text, model_choice)
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
    import io, math, os
    from PIL import Image, ImageEnhance, ImageDraw
    from huggingface_hub import InferenceClient
    from dotenv import load_dotenv

    load_dotenv()

    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        OCR_AVAILABLE = True
    except Exception:
        OCR_AVAILABLE = False

    # ── Hugging Face config ───────────────────────────────────
    HF_TOKEN = st.secrets.get("HF_TOKEN") or os.environ.get("HF_TOKEN")

    HF_MODELS = {
        "⚡ FLUX Schnell (Fastest)":    "black-forest-labs/FLUX.1-schnell",
        "🏆 FLUX Dev    (Best Quality)": "black-forest-labs/FLUX.1-dev",
        "🎨 SD v2       (Classic)":      "stabilityai/stable-diffusion-2",
    }

    # ── helper: generate image via HF InferenceClient ────────
    def generate_image_hf(prompt: str, model_id: str) -> Image.Image:
        client = InferenceClient(token=HF_TOKEN)
        image  = client.text_to_image(prompt=prompt, model=model_id)
        return image  # returns PIL Image directly

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

        model_id = st.selectbox(
          "🤖 Choose Model",
          [
              "black-forest-labs/FLUX.1-schnell",
              "black-forest-labs/FLUX.1-dev",
          ],
           help="FLUX Schnell = fastest | FLUX Dev = best quality"
       )
        st.caption(f"Model: `{model_id}`") 

        prompt     = st.text_area("📝 Prompt", placeholder="A futuristic city at sunset, oil painting style…")
        neg_prompt = st.text_input("🚫 Negative Prompt (optional)", placeholder="blurry, bad quality, ugly…")

        col_a, col_b = st.columns(2)
        with col_a:
            num_images = st.slider("Number of images", 1, 4, 1, key="gen_n")
        with col_b:
            st.info("💡 Image size is auto-selected by the model")

        if st.button("🚀 Generate", key="btn_gen"):
            if not prompt.strip():
                st.warning("Please enter a prompt.")
            elif not HF_TOKEN:
                st.error("HF_TOKEN not found. Add it to your .env or Streamlit Secrets.")
            else:
                generated = []
                progress  = st.progress(0, text="Starting…")

                for i in range(num_images):
                    progress.progress(
                        int((i / num_images) * 100),
                        text=f"Generating image {i+1} of {num_images}… (may take 20–40s)"
                    )
                    try:
                        full_prompt = prompt
                        if neg_prompt.strip():
                            full_prompt += f", not {neg_prompt}"

                        img = generate_image_hf(full_prompt, model_id)
                        generated.append(img)

                    except Exception as e:
                        st.error(f"Image {i+1} failed: {e}")

                progress.progress(100, text="Done!")

                if generated:
                    st.success(f"✅ {len(generated)} image(s) generated!")
                    captions = [f"#{i+1} • {model_id.split('/')[1]}" for i in range(len(generated))]
                    render_image_grid(generated, captions)

    # ═══════════════════════════════════════════════════════════
    # 🔁 TAB 2 — VARIATIONS
    # ═══════════════════════════════════════════════════════════
    with tab_var:
        st.subheader("Image Variations")
        st.caption("Upload an image, describe it, and generate similar variations using your chosen model.")

        var_model_label = st.selectbox("🤖 Model", list(HF_MODELS.keys()), key="var_model")
        var_model_id    = HF_MODELS[var_model_label]

        var_file   = st.file_uploader("Upload source image", type=["png", "jpg", "jpeg"], key="var_up")
        var_prompt = st.text_input(
            "📝 Describe the image (used as base prompt)",
            placeholder="A portrait of a woman in blue…",
            key="var_prompt"
        )
        var_n = st.slider("Number of variations", 1, 4, 2, key="var_n")

        if var_file:
            src_img = Image.open(var_file)
            st.image(src_img, caption="Source image", width=300)

            if st.button("🔁 Generate Variations", key="btn_var"):
                if not var_prompt.strip():
                    st.warning("Please describe the image to guide variations.")
                elif not HF_TOKEN:
                    st.error("HF_TOKEN not found.")
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
                            img    = generate_image_hf(varied, var_model_id)
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
        st.caption("Describe what you want to change and generate new versions with that edit applied.")

        edit_model_label = st.selectbox("🤖 Model", list(HF_MODELS.keys()), key="edit_model")
        edit_model_id    = HF_MODELS[edit_model_label]

        edit_file   = st.file_uploader("Upload image to edit", type=["png", "jpg", "jpeg"], key="edit_up")
        edit_prompt = st.text_area(
            "✏️ Edit prompt",
            placeholder="Same scene but at night with neon lights…",
            key="edit_prompt"
        )
        edit_n = st.slider("Number of outputs", 1, 4, 1, key="edit_n")

        if edit_file:
            src_img = Image.open(edit_file).convert("RGB")
            st.image(src_img, caption="Image to edit", width=300)

            if st.button("✏️ Apply Edit", key="btn_edit"):
                if not edit_prompt.strip():
                    st.warning("Please enter an edit prompt.")
                elif not HF_TOKEN:
                    st.error("HF_TOKEN not found.")
                else:
                    edits    = []
                    progress = st.progress(0, text="Starting…")

                    for i in range(edit_n):
                        progress.progress(
                            int((i / edit_n) * 100),
                            text=f"Generating edit {i+1} of {edit_n}…"
                        )
                        try:
                            img = generate_image_hf(edit_prompt, edit_model_id)
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
                with st.spinner("Analyzing…"):
                    response = answer_query(
                        "Describe this image, explain insights, and possible meaning.",
                        model_choice
                    )
                st.write("### 🤖 AI Insight")
                st.write(response)

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

