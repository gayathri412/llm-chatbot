import re
from llm.client import chat_completion


# 🔢 Calculator Tool
def calculator_tool(query: str):
    try:
        clean_query = re.sub(r"[^0-9+\-*/(). ]", "", query)

        if not clean_query.strip():
            return "⚠️ Invalid calculation"

        result = eval(clean_query)

        return f"🧮 Result: {result}"

    except Exception:
        return "⚠️ Calculation error"


# 🔪 Chunking
def chunk_text(text, chunk_size=800):
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]


# 📄 File Analyzer Tool
maries = []


from llm.client import chat_completion

def file_analyzer_tool(text: str, model_choice="Llama"):

    # 🔪 chunk
    chunk_size = 800
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

    partials = []

    for chunk in chunks[:2]:
        prompt = f"""
Create a clean and well-structured summary.

FORMAT STRICTLY:

## Title

### Overview
(2–3 lines summary)

### Key Statistics
- Point 1
- Point 2
- Point 3

### Risk Factors / Insights
- Insight 1
- Insight 2
- Insight 3

RULES:
- Use bullet points
- Keep it clean and readable
- Do NOT write long paragraphs

Content:
{partials}

Final Output:
"""