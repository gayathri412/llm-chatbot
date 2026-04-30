from app.tools import calculator_tool, file_analyzer_tool
from data.json_fallback import fetch_context
from llm.client import chat_completion


# 🔧 TOOL DECISION (LLM-based)
def decide_tool_llm(query, model_choice):

    tool_prompt = f"""
You are an AI assistant that selects tools.

Available tools:
1. calculator - ONLY for math calculations (e.g., "2+2", "what is 15% of 200", "sqrt(16)")
2. file - ONLY for analyzing uploaded file content
3. none - for all general questions, explanations, facts, research

Question: {query}

Reply ONLY with one word:
calculator OR file OR none
"""

    messages = [
        {"role": "system", "content": "You are a tool selector."},
        {"role": "user", "content": tool_prompt}
    ]

    try:
        decision = chat_completion(messages, model_choice)

        # ✅ safety checks
        if not decision or not isinstance(decision, str):
            return "none"

        decision = decision.strip().lower()

        # sometimes model returns sentence → take first word
        decision = decision.split()[0]

        # ✅ enforce valid outputs
        if decision not in ["calculator", "file", "none"]:
            return "none"

        return decision

    except Exception as e:
        print("Tool decision error:", e)
        return "none"


# 🧠 MAIN FUNCTION
def answer_query(query, model_choice="Llama"):

    # 🔍 Extract latest question
    if "The user now asks:" in query:
        latest_question = query.split("The user now asks:")[-1].strip()
    else:
        latest_question = query.strip()

    # 📄 FILE HANDLING (large input)
    if len(query) > 1000:
        return file_analyzer_tool(query, model_choice)

    # 🔧 TOOL DECISION
    tool = decide_tool_llm(latest_question, model_choice)

    if tool == "calculator":
        return calculator_tool(latest_question)

    # 🔍 RAG context
    context = fetch_context(latest_question)
    context_text = "\n".join(context) if context else ""

    # 🧠 FINAL PROMPT
    final_prompt = f"""
You are a smart and helpful AI assistant.

Answer the user's question clearly and accurately.

Instructions:
- Use context if available
- Otherwise use general knowledge
- Keep explanation simple and clear

User Question:
{latest_question}

Context:
{context_text}

Answer:
"""

    messages = [
        {"role": "system", "content": "You are a helpful AI assistant."},
        {"role": "user", "content": final_prompt}
    ]

    try:
        return chat_completion(messages, model_choice)
    except Exception as e:
        return f"Error: {str(e)}"