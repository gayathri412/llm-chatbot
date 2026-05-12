import html
import io

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pdfplumber
import streamlit as st
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sklearn.linear_model import LinearRegression


def _build_pdf_report(title, report_text):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()

    safe_report = html.escape(report_text).replace("\n", "<br/>")
    content = [
        Paragraph(title, styles["Title"]),
        Spacer(1, 12),
        Paragraph(safe_report, styles["Normal"]),
    ]

    doc.build(content)
    buffer.seek(0)
    return buffer.getvalue()


def render_charts_page(model_choice, answer_query):
    st.title("📊 AI Data Analytics + Prediction")
    file = st.file_uploader(
        "📂 Upload CSV or PDF",
        type=["csv", "pdf"]
    )

    question = st.text_input(
         "Ask something about your data or document",
         placeholder="Type your question here..."
    )

    if not file:
        return

    st.success(f"Uploaded: {file.name}")

    if file.name.endswith(".csv"):
        try:
            # Try different encodings
            encodings = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']
            df = None
            for encoding in encodings:
                try:
                    df = pd.read_csv(file, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                st.error("Could not read the CSV file. Please check the file format.")
                return
            
            # Remove empty columns and rows
            df = df.dropna(axis=1, how='all')  # Drop empty columns
            df = df.dropna(axis=0, how='all')  # Drop empty rows
            df = df.loc[:, ~df.columns.duplicated()]  # Remove duplicate columns

            if df.empty:
                st.error("The CSV file appears to be empty or contains no valid data.")
                return

            st.write("### Data Preview")
            st.dataframe(df.head())
            
            st.write(f"### Dataset Info")
            st.write(f"Shape: {df.shape[0]} rows, {df.shape[1]} columns")
            st.write(f"Columns: {list(df.columns)}")
            
        except Exception as e:
            st.error(f"Error reading CSV file: {str(e)}")
            return

        st.write("### Data Explanation")
        summary = df.describe(include="all").to_string()

        explanation = answer_query(
            f"Explain this dataset:\n{summary}",
            model_choice,
        )
        st.write(explanation)

        cols = df.columns.tolist()
        x_col = st.selectbox("X-axis", cols)
        y_col = st.selectbox("Y-axis", cols)

        if x_col != y_col:
            df[y_col] = pd.to_numeric(df[y_col], errors="coerce")
            chart_data = df[[x_col, y_col]].dropna()

            if not chart_data.empty:
                st.write("### Visualization")

                chart_type = st.selectbox(
                    "Chart Type",
                    ["Line", "Bar", "Scatter"],
                )

                if chart_type == "Line":
                    st.line_chart(chart_data, x=x_col, y=y_col)

                elif chart_type == "Bar":
                    st.bar_chart(chart_data, x=x_col, y=y_col)

                elif chart_type == "Scatter":
                    fig, ax = plt.subplots()
                    ax.scatter(chart_data[x_col], chart_data[y_col])
                    ax.set_xlabel(x_col)
                    ax.set_ylabel(y_col)
                    st.pyplot(fig)
                    plt.close(fig)

                st.write("### Analysis")
                analysis = answer_query(
                    f"Analyze trends:\n{summary}",
                    model_choice,
                )
                st.write(analysis)

                st.write("### Prediction")

                X = np.arange(len(chart_data)).reshape(-1, 1)
                y = chart_data[y_col].values

                model = LinearRegression()
                model.fit(X, y)

                future = np.arange(len(X), len(X) + 5).reshape(-1, 1)
                pred = model.predict(future)

                st.write(pred)

                pred_df = pd.DataFrame({
                    "Index": list(range(len(y) + len(pred))),
                    "Value": np.concatenate([y, pred]),
                })

                st.line_chart(pred_df, x="Index", y="Value")

                report = f"""
Explanation:
{explanation}

Analysis:
{analysis}

Prediction:
{pred}
"""

                st.download_button(
                    "Download Report",
                    _build_pdf_report("CSV Report", report),
                    "csv_report.pdf",
                    "application/pdf",
                )

            else:
                st.warning("No numeric data found for the selected Y-axis.")

    elif file.name.endswith(".pdf"):
        text = ""

        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""

        st.text_area("Content", text[:2000])

        explanation = answer_query(
            f"Explain this document:\n{text[:2000]}",
            model_choice,
        )
        st.write("### Explanation")
        st.write(explanation)

        analysis = answer_query(
            f"Analyze this document:\n{text[:2000]}",
            model_choice,
        )
        st.write("### Analysis")
        st.write(analysis)

        prediction = answer_query(
            f"Predict outcomes:\n{text[:2000]}",
            model_choice,
        )
        st.write("### Prediction")
        st.write(prediction)

        report = f"""
Explanation:
{explanation}

Analysis:
{analysis}

Prediction:
{prediction}
"""

        st.download_button(
            "Download Report",
            _build_pdf_report("PDF Report", report),
            "document_report.pdf",
            "application/pdf",
        )

    st.write("### Ask More")

    follow_up = st.text_input("Ask about the file")

    if follow_up:
        if file.name.endswith(".csv"):
            context = df.describe(include="all").to_string()
        else:
            context = text[:2000]

        reply = answer_query(
            f"Context:\n{context}\n\nQuestion:\n{follow_up}",
            model_choice,
        )

        st.write(reply)
