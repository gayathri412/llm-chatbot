from app.tools import calculator_tool, file_analyzer_tool
from data.json_fallback import fetch_context
from llm.client import chat_completion


def decide_tool(query: str):
    query = query.lower()

    if any(char.isdigit() for char in query):
        return "calculator"

    if "file" in query or "analyze" in query:
        return "file"

    return "none"


def answer_query(query, model_choice="Llama"):

    # 🔍 Extract latest question
    if "The user now asks:" in query:
        latest_question = query.split("The user now asks:")[-1].strip()
    else:
        latest_question = query.strip()

    # 🔧 TOOL DECISION
    tool = decide_tool(latest_question)

    if tool == "calculator":
        return calculator_tool(latest_question)

    elif tool == "file":
        return file_analyzer_tool(latest_question)

    # 🔍 RAG context
    context = fetch_context(latest_question)
    context_text = "\n".join(context) if context else ""

    # 🧠 FINAL PROMPT
    final_prompt = f"""
You are a smart and helpful AI assistant.

Answer the user's question clearly, accurately, and confidently.

Instructions:
- If context is provided, use it.
- If context is missing or incomplete, use your general knowledge.
- Do NOT say "I don't have information" unless absolutely necessary.
- Explain in a simple and clear way.

User Question:
{latest_question}

Context (if available):
{context_text}

Answer:
"""

    # 💬 Messages
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant."},
        {"role": "user", "content": final_prompt}
    ]

    # 🤖 LLM response
    response = chat_completion(messages, model_choice)

    return response