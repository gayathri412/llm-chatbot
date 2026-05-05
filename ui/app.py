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
    st.session_state.page = "Home"
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

# Sidebar
st.sidebar.title("💬 SNTI")

nav_buttons = [
    ("🏠 Home", "Home"),
    ("➕ New Chat", "NewChat"),
    ("🔍 Search", "Search"),
    ("📊 Charts", "Charts"),
    ("️ Images", "Images"),
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

# =========================================
# 🏠 HOME PAGE
# =========================================
if page == "Home":
    st.markdown("""
    <div style='text-align:center; margin-top:100px;'>
        <h1 style='font-size:50px; color:#fbbf24;'>🤖 SNTI AI</h1>
        <p style='font-size:20px; color:#888; margin-top:20px;'>Your Intelligent Assistant for Everything</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        ### 💬 Chat
        Have intelligent conversations with AI
        """)
        if st.button("Start Chatting", key="home_chat"):
            st.session_state.page = "Chat"
            st.rerun()
    
    with col2:
        st.markdown("""
        ### 📊 Charts
        Analyze data with AI-powered insights
        """)
        if st.button("Analyze Data", key="home_charts"):
            st.session_state.page = "Charts"
            st.rerun()
    
    with col3:
        st.markdown("""
        ### 🖼️ Images
        Generate AI images with Pollinations
        """)
        if st.button("Create Images", key="home_images"):
            st.session_state.page = "Images"
            st.rerun()
    
    st.markdown("---")
    
    # Quick stats or recent activity
    st.markdown("### 🚀 Quick Access")
    
    col4, col5, col6, col7 = st.columns(4)
    with col4:
        if st.button("🔍 Search", use_container_width=True):
            st.session_state.page = "Search"
            st.rerun()
    with col5:
        if st.button("📱 AI Tools", use_container_width=True):
            st.session_state.page = "Apps"
            st.rerun()
    with col6:
        if st.button("🧠 Research", use_container_width=True):
            st.session_state.page = "Research"
            st.rerun()
    with col7:
        if st.button("💻 Codex", use_container_width=True):
            st.session_state.page = "Codex"
            st.rerun()

# =========================================
# 💬 CHAT PAGE
# =========================================
elif page == "Chat":
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
    
    # ---------- DATA SOURCE SELECTION ----------
    data_source = st.selectbox("📡 Select Data Source", ["Upload File", "BigQuery"])
    
    df = None
    
    if data_source == "BigQuery":
        st.markdown("### 🔗 BigQuery Connection")
        bq_project = st.text_input("Project ID", placeholder="my-project-123")
        bq_dataset = st.text_input("Dataset", placeholder="my_dataset")
        bq_table = st.text_input("Table", placeholder="my_table")
        
        if st.button("Connect to BigQuery"):
            with st.spinner("Connecting to BigQuery..."):
                try:
                    from google.cloud import bigquery
                    client = bigquery.Client(project=bq_project)
                    query = f"SELECT * FROM `{bq_project}.{bq_dataset}.{bq_table}` LIMIT 1000"
                    df = client.query(query).to_dataframe()
                    st.success(f"✅ Connected! Loaded {len(df)} rows")
                    st.dataframe(df.head())
                except Exception as e:
                    st.error(f"❌ BigQuery connection failed: {e}")
                    st.info("💡 Note: BigQuery requires `google-cloud-bigquery` library and authentication setup")
    
    else:
        file = st.file_uploader("📂 Upload CSV or PDF", type=["csv", "pdf"])
        
        if file:
            st.success(f"Uploaded: {file.name}")
            if file.name.endswith(".csv"):
                df = pd.read_csv(file)
                df = df.loc[:, ~df.columns.duplicated()]
            elif file.name.endswith(".pdf"):
                with pdfplumber.open(file) as pdf:
                    text = ""
                    for page in pdf.pages:
                        text += page.extract_text() or ""
                st.text_area("PDF Content", text[:2000])
    
    # ---------- SAMPLE VISUALIZATIONS (Show when no data) ----------
    if df is None:
        st.markdown("---")
        st.markdown("### 📈 Sample Analytics Dashboard")
        
        # Create sample data
        sample_data = pd.DataFrame({
            'Month': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            'Sales': [120, 135, 148, 162, 175, 190],
            'Revenue': [12000, 13500, 14800, 16200, 17500, 19000],
            'Users': [850, 920, 1050, 1180, 1320, 1450]
        })
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 Sales Trend")
            st.line_chart(sample_data.set_index('Month')[['Sales', 'Revenue']])
        
        with col2:
            st.markdown("#### 👥 User Growth")
            st.bar_chart(sample_data.set_index('Month')['Users'])
        
        st.markdown("---")
        st.markdown("### 📤 Upload Your Data")
        st.info("👆 Upload a CSV or PDF file above to analyze your own data with AI-powered insights!")
        
    else:
        # Data Analysis Section
        styles = getSampleStyleSheet()

    if file:
        st.success(f"Uploaded: {file.name}")

        styles = getSampleStyleSheet()

        # ================= CSV =================
        if file.name.endswith(".csv"):
            try:
                df = pd.read_csv(file)
                if df.empty:
                    st.warning("⚠️ The CSV file is empty. Please upload a file with data.")
                    df = None
                else:
                    df = df.loc[:, ~df.columns.duplicated()]
            except pd.errors.EmptyDataError:
                st.error("❌ The CSV file is empty. Please upload a file with data.")
                df = None
            except Exception as e:
                st.error(f"❌ Error reading CSV: {e}")
                df = None

            if df is not None:
                st.write("### 📄 Data Preview")
                st.dataframe(df.head())

                # --------- AUTO VISUALIZATIONS FROM DATA ----------
                st.markdown("---")
                st.write("### 📊 Auto-Generated Visualizations")
                
                # Find numeric columns for visualization
                numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
                
                viz_col1, viz_col2 = st.columns(2)
                
                with viz_col1:
                    if len(numeric_cols) >= 2:
                        st.markdown(f"#### 📈 {numeric_cols[0]} vs {numeric_cols[1]}")
                        chart_df = df[[numeric_cols[0], numeric_cols[1]]].dropna()
                        if not chart_df.empty:
                            st.line_chart(chart_df)
                    elif len(numeric_cols) >= 1 and len(categorical_cols) >= 1:
                        st.markdown(f"#### 📈 {categorical_cols[0]} vs {numeric_cols[0]}")
                        chart_df = df[[categorical_cols[0], numeric_cols[0]]].dropna().head(20)
                        if not chart_df.empty:
                            st.bar_chart(chart_df.set_index(categorical_cols[0]))
                
                with viz_col2:
                    if len(numeric_cols) >= 3:
                        st.markdown(f"#### 📊 {numeric_cols[2]} Distribution")
                        st.bar_chart(df[numeric_cols[2]].head(20))
                    elif len(numeric_cols) >= 1:
                        st.markdown(f"#### 📊 {numeric_cols[0]} Trend")
                        st.line_chart(df[numeric_cols[0]].head(50))

                # --------- EXPLAIN ----------
                st.markdown("---")
                st.write("### 🤖 Data Explanation")
                summary = df.describe(include='all').to_string()

                explanation = answer_query(
                    f"Explain this dataset:\n{summary}",
                    model_choice
                )
                st.write(explanation)

                # --------- CUSTOM ANALYSIS ----------
                st.markdown("---")
                st.write("### 🔍 Custom Analysis")
                
                cols = df.columns.tolist()
                col1, col2 = st.columns(2)
                with col1:
                    x_col = st.selectbox("X-axis", cols, key="x_custom")
                with col2:
                    y_col = st.selectbox("Y-axis", cols, key="y_custom")

                if x_col != y_col:
                    df[y_col] = pd.to_numeric(df[y_col], errors='coerce')
                    chart_data = df[[x_col, y_col]].dropna()

                    if not chart_data.empty:
                        st.write("### 📊 Custom Visualization")

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
                        st.write("### 📊 AI Analysis")

                        analysis = answer_query(
                            f"Analyze trends between {x_col} and {y_col}:\n{chart_data.describe().to_string()}",
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

                        st.write(f"Next 5 predicted values for {y_col}:")
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

elif page == "Images":
    st.title("🖼️ Image AI Studio")
    
    # ---------- POLLINATIONS AI IMAGE GENERATION ----------
    st.markdown("### 🤖 AI Image Generation (Pollinations)")
    
    img_prompt = st.text_area("Describe the image you want to generate...", 
                               placeholder="A futuristic city with flying cars, cyberpunk style, neon lights...")
    
    col_img1, col_img2, col_img3 = st.columns([1, 1, 2])
    with col_img1:
        img_width = st.selectbox("Width", [1024, 512, 768], index=0)
    with col_img2:
        img_height = st.selectbox("Height", [1024, 512, 768], index=0)
    with col_img3:
        img_seed = st.number_input("Seed (0 for random)", min_value=0, max_value=999999, value=0)
    
    if st.button("🎨 Generate Image", type="primary"):
        if img_prompt.strip():
            with st.spinner("Generating image with Pollinations AI..."):
                try:
                    # Pollinations AI API
                    seed = img_seed if img_seed > 0 else None
                    encoded_prompt = requests.utils.quote(img_prompt)
                    img_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={img_width}&height={img_height}&nologo=true"
                    if seed:
                        img_url += f"&seed={seed}"
                    
                    # Display generated image
                    st.image(img_url, caption=f"Generated: {img_prompt[:50]}...", use_column_width=True)
                    
                    # Download button
                    response = requests.get(img_url, timeout=60)
                    if response.status_code == 200:
                        st.download_button(
                            "📥 Download Image",
                            response.content,
                            f"generated_{img_seed or 'random'}.png",
                            "image/png"
                        )
                except Exception as e:
                    st.error(f"Error generating image: {str(e)}")
        else:
            st.warning("Please enter a description for the image.")
    
    st.markdown("---")
    st.info("💡 Tip: Use detailed prompts for better results. Example: 'A serene Japanese garden with cherry blossoms, golden hour lighting, 8k quality'")

elif page == "Apps":
    st.title("📱 AI Tools Hub")
    
    # ---------- SEARCH BAR ----------
    search_query = st.text_input("🔍 Search tools...", placeholder="Type to filter apps...")
    
    st.markdown("---")

    import pandas as pd
    import numpy as np
    import requests
    import re

    # ---------- SELECT APP ----------
    all_apps = [
        "📄 PDF Analyzer",
        "📊 CSV Analyzer",
        "🧾 Resume Analyzer",
        "🔐 Password Tester",
        "💬 Writing Assistant"
    ]
    
    # Filter apps based on search
    if search_query:
        filtered_apps = [app for app in all_apps if search_query.lower() in app.lower()]
        if not filtered_apps:
            st.info("No tools found matching your search.")
            filtered_apps = all_apps
    else:
        filtered_apps = all_apps
    
    app = st.selectbox("Choose App", filtered_apps)

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
        st.markdown("### 🔐 Password Strength Tester")
        st.markdown("Enter a password to check its strength.")
        
        password = st.text_input("Enter Password", type="password", key="pwd_input")

        def check_strength(p):
            score = 0
            feedback = []
            
            if len(p) >= 8:
                score += 1
            else:
                feedback.append("❌ At least 8 characters")
                
            if re.search(r"[A-Z]", p):
                score += 1
            else:
                feedback.append("❌ At least one uppercase letter")
                
            if re.search(r"[0-9]", p):
                score += 1
            else:
                feedback.append("❌ At least one number")
                
            if re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", p):
                score += 1
            else:
                feedback.append("❌ At least one special character")
                
            return score, feedback

        if password:
            score, feedback = check_strength(password)
            
            # Progress bar
            st.progress(score / 4)
            
            if score <= 1:
                st.error(f"🔴 Weak Password ({score}/4)")
                st.markdown("**Requirements to improve:**")
                for item in feedback:
                    st.markdown(f"- {item}")
            elif score == 2:
                st.warning(f"🟡 Moderate Password ({score}/4)")
                st.markdown("**Requirements to improve:**")
                for item in feedback:
                    st.markdown(f"- {item}")
            else:
                st.success(f"🟢 Strong Password ({score}/4) ✅")
                st.markdown("Great! Your password meets all security requirements.")

    # =========================================================
    # 💬 WRITING ASSISTANT
    # =========================================================
    elif app == "💬 Writing Assistant":
        text = st.text_area("Enter Text", height=150)

        action = st.selectbox("Choose Action", [
            "Rewrite",
            "Summarize",
            "Fix Grammar"
        ])
        
        # Detailed prompts for each action
        action_prompts = {
            "Rewrite": """Rewrite the following text to improve clarity, flow, and readability while maintaining the original meaning. 
            Use varied vocabulary, better sentence structures, and a professional tone:
            
            {text}""",
            
            "Summarize": """Provide a concise summary of the following text. 
            Capture the main points and key ideas in 2-3 short paragraphs or bullet points:
            
            {text}""",
            
            "Fix Grammar": """Correct all grammar, spelling, punctuation, and style issues in the following text. 
            Provide the corrected version with brief explanations of major changes made:
            
            {text}"""
        }

        if st.button("Process", type="primary"):
            if text.strip():
                with st.spinner(f"Processing with {action}..."):
                    prompt = action_prompts[action].format(text=text)
                    result = answer_query(prompt, model_choice)
                
                st.markdown("### ✨ Result:")
                st.write(result)
            else:
                st.warning("⚠️ Please enter some text to process.")

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
