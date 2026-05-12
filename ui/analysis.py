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


def _render_precise_bar_chart(data, x_col, y_col, title=None, max_bars=30):
    bar_data = data[[x_col, y_col]].copy()
    bar_data[y_col] = pd.to_numeric(bar_data[y_col], errors="coerce")
    bar_data = bar_data.dropna(subset=[x_col, y_col])

    if bar_data.empty:
        st.warning("No numeric values available for this bar chart.")
        return False

    bar_data["_label"] = bar_data[x_col].astype(str).str.strip()
    bar_data["_label"] = bar_data["_label"].replace("", "(blank)")
    bar_data = (
        bar_data.groupby("_label", sort=False, as_index=False)[y_col]
        .sum()
        .rename(columns={"_label": x_col})
    )

    if len(bar_data) > max_bars:
        bar_data = (
            bar_data.assign(_abs_value=bar_data[y_col].abs())
            .sort_values("_abs_value", ascending=False)
            .head(max_bars)
            .drop(columns="_abs_value")
        )

    positions = np.arange(len(bar_data))
    labels = bar_data[x_col].astype(str).tolist()
    values = bar_data[y_col].to_numpy()
    fig_width = min(18, max(9, len(bar_data) * 0.45))

    fig, ax = plt.subplots(figsize=(fig_width, 5.5))
    bars = ax.bar(positions, values, width=0.72)
    ax.set_xticks(positions)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title(title or f"{y_col} by {x_col}")
    ax.grid(axis="y", alpha=0.25)

    if len(bar_data) <= 15:
        ax.bar_label(bars, fmt="%.3g", padding=3)

    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
    return True


def render_charts_page(model_choice, answer_query):
    st.title("📊 AI Data Analytics + Prediction")
    
    # Data source selection
    data_source = st.selectbox("📡 Select Data Source", ["Upload CSV", "Upload Excel", "Upload PDF"])
    
    if data_source == "Upload CSV":
        file = st.file_uploader(
            "📂 Upload CSV file",
            type=["csv"],
            key="csv_upload",
            help="Maximum file size: 500MB. Supports CSV files with various encodings."
        )
    elif data_source == "Upload Excel":
        file = st.file_uploader(
            "📂 Upload Excel file",
            type=["xlsx", "xls"],
            key="excel_upload",
            help="Maximum file size: 500MB. Supports .xlsx and .xls files."
        )
    else:  # Upload PDF
        file = st.file_uploader(
            "📂 Upload PDF file",
            type=["pdf"],
            key="pdf_upload",
            help="Maximum file size: 500MB. For document analysis only."
        )

    question = st.text_input(
         "Ask something about your data or document",
         placeholder="Type your question here..."
    )

    if not file:
        return

    st.success(f"Uploaded: {file.name}")

    if data_source in ["Upload CSV", "Upload Excel"]:
        # Process CSV/Excel files with charts
        try:
            st.write("### Debug: File Information")
            st.write(f"File name: {file.name}")
            st.write(f"File type: {file.type}")
            st.write(f"File size: {len(file.getvalue())} bytes")
            
            # Handle different file types
            import io
            df = None
            last_error = None
            
            if data_source == "Upload Excel":
                # Direct Excel reading
                try:
                    file.seek(0)
                    excel_data = file.read()
                    df = pd.read_excel(io.BytesIO(excel_data))
                    st.success("Successfully read Excel file")
                    st.write(f"Shape: {df.shape}")
                    st.write(f"Columns: {list(df.columns)}")
                except Exception as e:
                    st.error(f"Error reading Excel file: {str(e)}")
                    return
            else:  # Upload CSV
                # Get file content as string first
                file.seek(0)
                content = file.read().decode('utf-8', errors='replace')
                
                st.write("### Debug: File Content Preview")
                st.code(content[:500])
                
                if not content.strip():
                    st.error("File appears to be completely empty.")
                    return
                
                lines = content.strip().split('\n')
                st.write(f"Found {len(lines)} lines in file")
                
                if len(lines) < 2:
                    st.error("File needs at least a header and one data row.")
                    return
                
                # Try to parse with pandas using StringIO
                delimiters = [',', ';', '\t', '|']
                for delimiter in delimiters:
                    try:
                        df = pd.read_csv(io.StringIO(content), delimiter=delimiter)
                        if len(df.columns) > 1 and len(df) > 0:
                            st.success(f"Successfully parsed CSV with '{delimiter}' delimiter")
                            st.write(f"Shape: {df.shape}")
                            st.write(f"Columns: {list(df.columns)}")
                            break
                        else:
                            df = None
                    except Exception as e:
                        last_error = e
                        continue
                
                # If CSV parsing failed, try Excel as fallback
                if df is None:
                    try:
                        file.seek(0)
                        excel_data = file.read()
                        df = pd.read_excel(io.BytesIO(excel_data))
                        st.success("Successfully read as Excel file (CSV fallback)")
                    except Exception as e:
                        st.error(f"Could not parse CSV file: {last_error}")
                        st.write("Please ensure the file is a proper CSV file.")
                        return
            
            # Debug info
            st.write("### Debug: DataFrame Info")
            st.write(f"DataFrame shape: {df.shape}")
            st.write(f"DataFrame columns: {list(df.columns)}")
            st.write(f"First few rows:\n{df.head(3).to_string()}")
            
            # Remove empty columns and rows (less aggressive)
            original_shape = df.shape
            df_cleaned = df.copy()
            
            # Only drop columns that are completely empty
            empty_cols = df_cleaned.columns[df_cleaned.isnull().all()].tolist()
            if empty_cols:
                df_cleaned = df_cleaned.drop(columns=empty_cols)
                st.write(f"Dropped empty columns: {empty_cols}")
            
            # Only drop rows that are completely empty
            empty_rows = df_cleaned[df_cleaned.isnull().all(axis=1)].index.tolist()
            if empty_rows:
                df_cleaned = df_cleaned.drop(index=empty_rows)
                st.write(f"Dropped {len(empty_rows)} completely empty rows")
            
            # Remove duplicate columns
            df_cleaned = df_cleaned.loc[:, ~df_cleaned.columns.duplicated()]
            
            st.write(f"### Debug: After Cleaning")
            st.write(f"Original shape: {original_shape}")
            st.write(f"Cleaned shape: {df_cleaned.shape}")

            if df_cleaned.empty:
                st.error("The file appears to be empty after cleaning. Check if all rows/columns are empty.")
                st.write("Debug: Showing original DataFrame before cleaning:")
                st.dataframe(df.head())
                return
            
            # Use cleaned DataFrame
            df = df_cleaned

            st.write("### Data Preview")
            st.dataframe(df.head())
            
            st.write(f"### Dataset Info")
            st.write(f"Shape: {df.shape[0]} rows, {df.shape[1]} columns")
            st.write(f"Columns: {list(df.columns)}")
            
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")
            import traceback
            st.error(f"Full error: {traceback.format_exc()}")
            return

        st.write("### Data Explanation")
        summary = df.describe(include="all").to_string()

        explanation = answer_query(
            f"Explain this dataset:\n{summary}",
            model_choice,
        )
        st.write(explanation)

        # Get numeric and categorical columns
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
        all_cols = df.columns.tolist()
        
        st.write("### Visualization")
        
        # Chart type selection
        chart_type = st.selectbox(
            "Chart Type",
            ["Line", "Bar", "Scatter", "Pie", "Histogram", "Box Plot"],
        )
        
        if chart_type in ["Line", "Bar", "Scatter"]:
            # For these charts, we need X and Y axes
            x_col = st.selectbox("X-axis", all_cols)
            y_col = st.selectbox("Y-axis", numeric_cols)
            
            if x_col and y_col:
                # Convert Y to numeric
                df[y_col] = pd.to_numeric(df[y_col], errors="coerce")
                chart_data = df[[x_col, y_col]].dropna()
                
                if not chart_data.empty:
                st.warning("No categorical columns found for pie chart. Please select a column with text data.")
        
        elif chart_type == "Histogram":
            # For histogram, select a numeric column
            if numeric_cols:
                hist_col = st.selectbox("Select column for Histogram", numeric_cols)
                if hist_col:
                    fig, ax = plt.subplots(figsize=(10, 6))
                    ax.hist(df[hist_col].dropna(), bins=30, alpha=0.7, edgecolor='black')
                    ax.set_xlabel(hist_col)
                    ax.set_ylabel("Frequency")
                    ax.set_title(f"Distribution of {hist_col}")
                    st.pyplot(fig)
                    plt.close(fig)
            else:
                st.warning("No numeric columns found for histogram.")
        
        elif chart_type == "Box Plot":
            # For box plot, select a numeric column
            if numeric_cols:
                box_col = st.selectbox("Select column for Box Plot", numeric_cols)
                if box_col:
                    fig, ax = plt.subplots(figsize=(10, 6))
                    ax.boxplot(df[box_col].dropna())
                    ax.set_ylabel(box_col)
                    ax.set_title(f"Box Plot of {box_col}")
                    st.pyplot(fig)
                    plt.close(fig)
        
        st.write("### Prediction")
        
        # Enhanced prediction functionality
        if not df.empty and numeric_cols:
            prediction_col = st.selectbox("Select column for Prediction", numeric_cols)
            
            if prediction_col:
                # Prepare data for prediction
                pred_data = df[[prediction_col]].dropna()
                
                if not pred_data.empty:
                    st.write(f"### Prediction for {prediction_col}")
                    
                    # Show statistics
                    st.write(f"Data points: {len(pred_data)}")
                    st.write(f"Mean: {pred_data[prediction_col].mean():.2f}")
                    st.write(f"Std Dev: {pred_data[prediction_col].std():.2f}")
                    st.write(f"Min: {pred_data[prediction_col].min():.2f}")
                    st.write(f"Max: {pred_data[prediction_col].max():.2f}")
                    
                    # Linear Regression Prediction
                    X = np.arange(len(pred_data)).reshape(-1, 1)
                    y = pred_data[prediction_col].values

                    model = LinearRegression()
                    model.fit(X, y)

                    # Future predictions
                    future_periods = st.slider("Future periods to predict", min_value=1, max_value=20, value=5)
                    future = np.arange(len(X), len(X) + future_periods).reshape(-1, 1)
                    pred = model.predict(future)

                    # Display predictions
                    st.write("### Future Values")
                    pred_df = pd.DataFrame({
                        "Period": list(range(len(y), len(y) + future_periods)),
                        "Historical": list(y),
                        "Predicted": list(pred)
                    })
                    st.dataframe(pred_df)

                    # Visualization
                    fig, ax = plt.subplots(figsize=(12, 6))
                    ax.plot(pred_df["Period"][:len(y)], pred_df["Historical"], marker="o", label="Historical", linewidth=2)
                    ax.plot(pred_df["Period"][len(y):], pred_df["Predicted"], marker="x", linestyle="--", label="Predicted", linewidth=2)
                    ax.set_xlabel("Period")
                    ax.set_ylabel(prediction_col)
                    ax.set_title(f"{prediction_col} Prediction")
                    ax.legend()
                    ax.grid(True, alpha=0.3)
                    st.pyplot(fig)
                    plt.close(fig)
                    
                    # Prediction metrics
                    mse = np.mean((model.predict(X) - y) ** 2)
                    st.write(f"### Model Performance")
                    st.write(f"Mean Squared Error: {mse:.4f}")
                    st.write(f"R-squared: {model.score(X, y):.4f}")
                    
                    # Download predictions
                    pred_csv = pred_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label=" Download Predictions",
                        data=pred_csv,
                        file_name=f"predictions_{prediction_col}_{file.name}",
                        mime="text/csv",
                    )
                else:
                    st.warning("No valid data available for prediction.")
            else:
                st.warning("Please select a numeric column for prediction.")

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
        st.write(prediction)

        model = LinearRegression()
        model.fit(X, y)

        future = np.arange(len(X), len(X) + 5).reshape(-1, 1)
        pred = model.predict(future)

        st.write("Future predictions:", pred)

        pred_df = pd.DataFrame({
            "Index": list(range(len(y) + len(pred))),
            "Value": np.concatenate([y, pred]),
        })

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(pred_df["Index"][:len(y)], pred_df["Value"][:len(y)], marker="o", label="Historical")
        ax.plot(pred_df["Index"][len(y):], pred_df["Value"][len(y):], marker="x", linestyle="--", label="Predicted")
        ax.set_xlabel("Index")
        ax.set_ylabel(y_col)
        ax.legend()
        ax.grid(True, alpha=0.25)
        st.pyplot(fig)
        plt.close(fig)

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
            _build_pdf_report("Document Analysis Report", report),
            "document_report.pdf",
            "application/pdf",
        )
    elif data_source == "Upload PDF":
        # Process PDF files without charts
        try:
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
                _build_pdf_report("Document Analysis Report", report),
                "document_report.pdf",
                "application/pdf",
            )
        except Exception as e:
            st.error(f"Error processing PDF: {str(e)}")
            return

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
