import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
from app.orchestrator import answer_query

# ---------- UI STYLE ----------
st.markdown("""
<style>
/* Sidebar button styling */
[data-testid="stSidebar"] .stButton > button {
    width: 100%;
    text-align: left;
    padding: 10px 15px;
    margin: 2px 0;
    border-radius: 8px;
    background: transparent;
    border: 1px solid #333;
    color: #fbbf24;
    font-weight: 500;
    transition: all 0.2s ease;
}

[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(251, 191, 36, 0.1);
    border-color: #fbbf24;
    transform: translateX(3px);
}

[data-testid="stSidebar"] {
    background: #0a0a0a !important;
}

.stTextInput input, .stTextArea textarea {
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

# Session state
if "page" not in st.session_state:
    st.session_state.page = "Chat"
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

# Sidebar
st.sidebar.title("💬 SNTI")

nav_buttons = [
    ("➕ New Chat", "NewChat"),
    ("🔍 Search", "Search"),
    ("📊 Charts", "Charts"),
    ("🗄️ Big Data", "BigData"),
    ("🖼️ Images", "Images"),
    ("📱 Apps", "Apps"),
    ("🧠 Research", "Research"),
    ("💻 Codex", "Codex"),
    ("🤖 GPTs", "GPTs"),
]

for label, page_key in nav_buttons:
    if st.sidebar.button(label, key=f"nav_{page_key}"):
        if page_key == "NewChat":
            name = f"Chat {len(st.session_state.chats)+1}"
            st.session_state.chats[name] = []
            st.session_state.current_chat = name
            st.session_state.page = "Chat"
        else:
            st.session_state.page = page_key
        st.rerun()

st.sidebar.markdown("---")
model_choice = st.sidebar.selectbox("Model", ["Llama", "Gemini"])

# Page routing
page = st.session_state.page

if page == "Chat":
    chat_history = st.session_state.chats[st.session_state.current_chat]
    if not chat_history:
        st.markdown(f"<h1 style='text-align:center;margin-top:150px;color:#fbbf24'>🤖 {model_choice}</h1>", unsafe_allow_html=True)
    for q, r in chat_history:
        st.chat_message("user").write(q)
        st.chat_message("assistant").write(r)
    user_input = st.chat_input("Ask anything...")
    if user_input:
        st.chat_message("user").write(user_input)
        with st.spinner("Thinking..."):
            response = answer_query(user_input, model_choice)
        st.chat_message("assistant").write(response)
        chat_history.append((user_input, response))

elif page == "Search":
    st.title("🔍 Smart Search")
    query = st.text_input("Search anything...")
    if query:
        with st.spinner("Searching..."):
            response = answer_query(f"Give a clear answer for: {query}", model_choice)
        st.write(response)

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

elif page == "BigData":
    st.title("🗄️ Big Data Query & Analytics")
    st.info("Big Data page - Connect to BigQuery and analyze large datasets")
    
    st.write("### Features:")
    st.write("- Connect to BigQuery")
    st.write("- Run SQL queries")
    st.write("- Analyze large datasets")
    st.write("- Export results")

elif page == "Images":
    st.title("🖼️ Image AI Studio")
    st.info("Images page - AI image generation and editing (Photo code preserved)")

elif page == "Apps":
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
