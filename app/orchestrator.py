from app.tools import calculator_tool, file_analyzer_tool, document_qa_tool
from data.json_fallback import fetch_context
from llm.client import chat_completion

def decide_tool_llm(query, model_choice):

    tool_prompt = f"""
You are an AI assistant that selects tools.

Available tools:
1. calculator → for math calculations
2. file → for summarizing, analyzing, or understanding uploaded documents
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

    decision = decision.split()[0]

    print("Tool selected:", decision)

    return decision

def decide_tool(query: str):
    query = query.lower()

    if any(char.isdigit() for char in query):
        return "calculator"

    if "file" in query or "analyze" in query:
        return "file"

    return "none"


from app.tools import calculator_tool, file_analyzer_tool, document_qa_tool

def answer_query(query, model_choice="Llama"):

    # 🔍 Extract latest question
    if "The user now asks:" in query:
        latest_question = query.split("The user now asks:")[-1].strip()
    else:
        latest_question = query.strip()

    # 🔥 FILE HANDLING (VERY IMPORTANT)
    if len(query) > 1000:   # means file content is passed

        # 👉 If user asked a question → Q&A
       question_words = ["what", "why", "how", "explain", "describe", "tell", "give", "list"]
       if any(word in latest_question.lower() for word in question_words):
              return document_qa_tool(latest_question, query, model_choice)
       
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