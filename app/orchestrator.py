from app.tools import calculator_tool, file_analyzer_tool
from data.json_fallback import fetch_context
from llm.client import chat_completion

def decide_tool_llm(query, model_choice):

    tool_prompt = f"""
You are an AI assistant that selects tools.

Available tools:
1. calculator → for math calculations
2. file → for analyzing documents
3. none → for normal questions

Question: {query}

Reply ONLY with:
calculator
file
none
"""

    messages = [
        {"role": "system", "content": "You are a tool selector."},
        {"role": "user", "content": tool_prompt}
    ]

    # ✅ FIRST get decision
    decision = chat_completion(messages, model_choice)

    # ✅ THEN clean it
    decision = decision.strip().lower()
    decision = decision.split()[0]

    return decision

from app.tools import calculator_tool, file_analyzer_tool

def answer_query(query, model_choice="Llama"):

    # 🔍 Extract latest question
    if "The user now asks:" in query:
        latest_question = query.split("The user now asks:")[-1].strip()
    else:
        latest_question = query.strip()


    if len(query) > 1000:
            return file_analyzer_tool(query, model_choice)

    # 🔧 TOOL DECISION (normal queries)
    tool = decide_tool_llm(latest_question, model_choice)

    if tool == "calculator":
        return calculator_tool(latest_question)

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

    messages = [
        {"role": "system", "content": "You are a helpful AI assistant."},
        {"role": "user", "content": final_prompt}
    ]

    return chat_completion(messages, model_choice)