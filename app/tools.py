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
You are an expert document summarizer.

Create a structured summary of this text with:
- Title (if possible)
- 4–6 bullet key points
- 1–2 line brief overview

Keep it clear and concise.

Text:
{chunk}

Structured Summary:
"""
        messages = [
            {"role": "system", "content": "You summarize documents clearly."},
            {"role": "user", "content": prompt}
        ]

        part = chat_completion(messages, model_choice)
        partials.append(part)

    # 🔥 combine
    final_prompt = f"""
Merge these into ONE clean structured summary.

Format:
## Title
**Overview:**
- ...
**Key Points:**
- ...
- ...
- ...

Content:
{partials}
"""
    messages = [
        {"role": "system", "content": "You merge summaries cleanly."},
        {"role": "user", "content": final_prompt}
    ]

    return chat_completion(messages, model_choice)