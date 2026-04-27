from prompts.compose import build_prompt
from llm.client import chat_completion
from data.json_fallback import fetch_context

def answer_query(query, model_choice="Llama"):

    # 🔍 Extract latest question properly
    if "The user now asks:" in query:
        latest_question = query.split("The user now asks:")[-1]
    else:
        latest_question = query

    # 🔍 RAG context
    context = fetch_context(latest_question)
    context_text = "\n".join(context) if context else "No relevant knowledge found."

    # 🧠 Final prompt
    final_prompt = f"""
You are an intelligent assistant.

Use the knowledge below to answer the question accurately.

Knowledge:
{context_text}

Conversation:
{query}

Answer clearly and correctly.
"""

    messages = build_prompt(final_prompt)

    response = chat_completion(messages, model_choice)

    return response