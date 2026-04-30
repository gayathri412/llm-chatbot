import time

from app.cache import answer_cache
from app.telemetry import log_chat_event
from app.tools import calculator_tool, file_analyzer_tool
from data.rag import format_context, retrieve_context
from llm.client import chat_completion


# TOOL DECISION (LLM-based)
def decide_tool_llm(query, model_choice):
    tool_prompt = f"""
You are an AI assistant that selects tools.

Available tools:
1. calculator - ONLY for explicit math calculations like "2+2", "15% of 200", "sqrt(16)", "5 * 8"
2. file - ONLY for analyzing uploaded file content
3. none - for ALL explanations, data analysis, facts, research, general questions

IMPORTANT:
- "Explain this dataset" -> use "none" (NOT calculator)
- "Analyze this data" -> use "none" (NOT calculator)
- Questions with numbers but asking for explanation -> use "none"
- Only use calculator for actual math problems to solve

Question: {query}

Reply ONLY with one word:
calculator OR file OR none
"""

    messages = [
        {"role": "system", "content": "You are a tool selector."},
        {"role": "user", "content": tool_prompt},
    ]

    try:
        decision = chat_completion(messages, model_choice)

        if not decision or not isinstance(decision, str):
            return "none"

        decision = decision.strip().lower()
        decision = decision.split()[0]

        if decision not in ["calculator", "file", "none"]:
            return "none"

        return decision

    except Exception as e:
        print("Tool decision error:", e)
        return "none"


def _status_for_response(response):
    return "error" if str(response).startswith("Error:") else "ok"


# MAIN FUNCTION
def answer_query(query, model_choice="Llama"):
    started_at = time.perf_counter()
    telemetry_query = query.split("\n\nFile content:", 1)[0].strip()
    cache_meta = answer_cache.metadata()

    def duration_ms():
        return int((time.perf_counter() - started_at) * 1000)

    def emit_event(response, status="ok", tool="none", cache_hit=False, context_items=None, error=""):
        log_chat_event(
            query=telemetry_query,
            model_choice=model_choice,
            duration_ms=duration_ms(),
            status=status,
            tool=tool,
            cache_hit=cache_hit,
            cache_backend=cache_meta["backend"],
            context_items=context_items or [],
            response=response,
            error=error,
        )

    if "The user now asks:" in query:
        latest_question = query.split("The user now asks:")[-1].strip()
    else:
        latest_question = query.strip()

    if len(query) > 1000:
        try:
            response = file_analyzer_tool(query, model_choice)
            emit_event(response, status=_status_for_response(response), tool="file")
            return response
        except Exception as e:
            response = f"Error: {str(e)}"
            emit_event(response, status="error", tool="file", error=str(e))
            return response

    tool = decide_tool_llm(latest_question, model_choice)

    if tool == "calculator":
        response = calculator_tool(latest_question)
        emit_event(response, status=_status_for_response(response), tool="calculator")
        return response

    retrieved_context = retrieve_context(latest_question)
    context_text = format_context(retrieved_context)
    cache_key = answer_cache.make_key(latest_question, model_choice, context_text)
    cached_response = answer_cache.get(cache_key)

    if cached_response:
        emit_event(cached_response, cache_hit=True, context_items=retrieved_context)
        return cached_response

    final_prompt = f"""
You are a smart and helpful AI assistant.

Answer the user's question clearly and accurately.

Instructions:
- First use the retrieved context when it is relevant
- If the context does not contain the answer, say that clearly and then use general knowledge
- Do not invent facts that are not supported by the context
- Keep explanation simple and clear

User Question:
{latest_question}

Retrieved Context:
{context_text if context_text else "No relevant local context found."}

Answer:
"""

    messages = [
        {"role": "system", "content": "You are a helpful AI assistant."},
        {"role": "user", "content": final_prompt},
    ]

    try:
        response = chat_completion(messages, model_choice)
        status = _status_for_response(response)

        if status == "ok":
            answer_cache.set(cache_key, response)

        emit_event(response, status=status, context_items=retrieved_context)
        return response
    except Exception as e:
        response = f"Error: {str(e)}"
        emit_event(response, status="error", context_items=retrieved_context, error=str(e))
        return response
