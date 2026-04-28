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
def file_analyzer_tool(text: str, model_choice="Llama"):

    chunks = chunk_text(text)
    summaries = []

    for chunk in chunks[:2]:  # limit to avoid overload
        prompt = f"""
Summarize this part of a document:

{chunk}
"""

        messages = [
            {"role": "system", "content": "You are a document summarizer."},
            {"role": "user", "content": prompt}
        ]

        summary = chat_completion(messages, model_choice)
        summaries.append(summary)

    # 🔥 Combine summaries
    final_prompt = f"""
Combine the following summaries into one clear final summary:

{summaries}
"""

    messages = [
        {"role": "system", "content": "You are a summarization expert."},
        {"role": "user", "content": final_prompt}
    ]

    final_response = chat_completion(messages, model_choice)

    return final_response
