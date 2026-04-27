from llm.client import chat_completion
from data.json_fallback import fetch_context


def answer_query(query, model_choice="Llama"):

    # 🔍 Extract latest question
    if "The user now asks:" in query:
        latest_question = query.split("The user now asks:")[-1].strip()
    else:
        latest_question = query.strip()

    # 🔍 Get context (RAG)
    context = fetch_context(latest_question)
    context_text = "\n".join(context) if context else ""

    # 🧠 Improved Prompt
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

    # 💬 Messages format (better than build_prompt)
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant."},
        {"role": "user", "content": final_prompt}
    ]

    # 🤖 Get response
    response = chat_completion(messages, model_choice)

    return response