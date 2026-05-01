import time

from app.cache import answer_cache
from app.telemetry import log_chat_event
from app.tools import calculator_tool, file_analyzer_tool
from data.rag import format_context, retrieve_context
from llm.client import chat_completion
from prompts.compose import build_rag_answer_prompt, build_tool_selection_prompt


# TOOL DECISION (LLM-based)
def decide_tool_llm(query, model_choice, temperature=0.0):
    messages = build_tool_selection_prompt(query)

    try:
        decision = chat_completion(messages, model_choice, temperature=temperature)

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


def _result(answer, include_trace=False, trace=None):
    if not include_trace:
        return answer

    trace = trace or {}
    return {
        "answer": answer,
        "used_context_count": trace.get("used_context_count", 0),
        "trace": trace,
    }


# MAIN FUNCTION
def answer_query(query, model_choice="Llama", include_trace=False, temperature=0.2):
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

    trace = {
        "query": latest_question,
        "model_choice": model_choice,
        "temperature": temperature,
        "tool": "none",
        "cache_hit": False,
        "cache_backend": cache_meta["backend"],
        "used_context_count": 0,
        "bq_hits": 0,
        "json_hits": 0,
        "context_sources": [],
    }

    if len(query) > 1000:
        try:
            response = file_analyzer_tool(query, model_choice)
            trace["tool"] = "file"
            trace["status"] = _status_for_response(response)
            emit_event(response, status=_status_for_response(response), tool="file")
            return _result(response, include_trace, trace)
        except Exception as e:
            response = f"Error: {str(e)}"
            trace["tool"] = "file"
            trace["status"] = "error"
            trace["error"] = str(e)
            emit_event(response, status="error", tool="file", error=str(e))
            return _result(response, include_trace, trace)

    tool = decide_tool_llm(latest_question, model_choice, temperature=0.0)
    trace["tool"] = tool

    if tool == "calculator":
        response = calculator_tool(latest_question)
        trace["status"] = _status_for_response(response)
        emit_event(response, status=_status_for_response(response), tool="calculator")
        return _result(response, include_trace, trace)

    retrieved_context = retrieve_context(latest_question)
    context_text = format_context(retrieved_context)
    trace["used_context_count"] = len(retrieved_context)
    trace["bq_hits"] = len([item for item in retrieved_context if item.get("backend") == "bigquery"])
    trace["json_hits"] = len([item for item in retrieved_context if item.get("backend") == "json"])
    trace["context_sources"] = [
        {
            "title": item.get("title"),
            "source": item.get("source"),
            "backend": item.get("backend", "unknown"),
            "score": item.get("score"),
        }
        for item in retrieved_context
    ]
    cache_key = answer_cache.make_key(latest_question, model_choice, context_text)
    cached_response = answer_cache.get(cache_key)

    if cached_response:
        trace["cache_hit"] = True
        trace["status"] = "ok"
        emit_event(cached_response, cache_hit=True, context_items=retrieved_context)
        return _result(cached_response, include_trace, trace)

    messages = build_rag_answer_prompt(latest_question, context_text)

    try:
        response = chat_completion(messages, model_choice, temperature=temperature)
        status = _status_for_response(response)

        if status == "ok":
            answer_cache.set(cache_key, response)

        trace["status"] = status
        emit_event(response, status=status, context_items=retrieved_context)
        return _result(response, include_trace, trace)
    except Exception as e:
        response = f"Error: {str(e)}"
        trace["status"] = "error"
        trace["error"] = str(e)
        emit_event(response, status="error", context_items=retrieved_context, error=str(e))
        return _result(response, include_trace, trace)


def answer_query_with_trace(query, model_choice="Llama", temperature=0.2):
    return answer_query(
        query,
        model_choice=model_choice,
        include_trace=True,
        temperature=temperature,
    )
