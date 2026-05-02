import time

from app.access_control import build_access_policy
from app.cache import answer_cache
from app.config import get_settings
from app.guardrails import (
    SAFE_COMPLETION,
    append_reference_notice,
    check_references,
    moderate_output,
    validate_prompt,
)
from app.language import build_language_context
from app.model_routing import select_model_for_query
from app.security import RedactionResult, redact_pii
from app.telemetry import log_chat_event
from app.token_budget import trim_to_token_budget
from app.tools import calculator_tool, file_analyzer_tool
from data.rag import format_context, retrieve_context
from llm.client import chat_completion
from prompts.compose import build_rag_answer_prompt, build_tool_selection_prompt


# TOOL DECISION (LLM-based)
def decide_tool_llm(query, model_choice, temperature=0.0, max_output_tokens=16):
    messages = build_tool_selection_prompt(query)

    try:
        decision = chat_completion(
            messages,
            model_choice,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

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


def _messages_to_text(messages):
    return "\n\n".join(
        f"{message.get('role', 'unknown')}: {message.get('content', '')}"
        for message in messages
    )


# MAIN FUNCTION
def answer_query(
    query,
    model_choice="Llama",
    include_trace=False,
    temperature=0.2,
    user_id="anonymous",
    user_context=None,
):
    started_at = time.perf_counter()
    settings = get_settings()
    requested_model_choice = model_choice
    effective_model_choice = model_choice
    user_context = dict(user_context or {})
    user_context.setdefault("user_id", user_id)
    access_policy = build_access_policy(user_context, settings)
    redaction = (
        redact_pii(query)
        if settings.pii_redaction_enabled
        else RedactionResult(query, False, {"emails": 0, "phones": 0})
    )
    safe_query = redaction.text
    telemetry_query = safe_query.split("\n\nFile content:", 1)[0].strip()
    cache_meta = answer_cache.metadata()

    def duration_ms():
        return int((time.perf_counter() - started_at) * 1000)

    def emit_event(
        response,
        status="ok",
        tool="none",
        cache_hit=False,
        context_items=None,
        error="",
        prompt_text="",
    ):
        log_chat_event(
            query=telemetry_query,
            model_choice=effective_model_choice,
            duration_ms=duration_ms(),
            status=status,
            tool=tool,
            cache_hit=cache_hit,
            cache_backend=cache_meta["backend"],
            context_items=context_items or [],
            response=response,
            error=error,
            user_id=user_id,
            prompt_text=prompt_text or telemetry_query,
            pii_redacted=redaction.redacted,
            pii_counts=redaction.counts,
        )

    if "The user now asks:" in safe_query:
        latest_question = safe_query.split("The user now asks:")[-1].strip()
    else:
        latest_question = safe_query.strip()

    safe_query_budget = trim_to_token_budget(safe_query, settings.max_input_tokens)
    latest_question_budget = trim_to_token_budget(latest_question, settings.max_input_tokens)
    safe_query_for_model = safe_query_budget.text
    latest_question = latest_question_budget.text
    answer_cache.record_query(latest_question)
    language_context = build_language_context(latest_question, settings)
    language_instructions = language_context.prompt_instructions

    trace = {
        "query": latest_question,
        "user_id": user_id,
        "requested_model_choice": requested_model_choice,
        "model_choice": effective_model_choice,
        "temperature": temperature,
        "tool": "none",
        "cache_hit": False,
        "cache_backend": cache_meta["backend"],
        "used_context_count": 0,
        "bq_hits": 0,
        "json_hits": 0,
        "context_sources": [],
        "pii_redacted": redaction.redacted,
        "pii_counts": redaction.counts,
        "prompt_validation": "not_checked",
        "output_moderation": "not_checked",
        "reference_checking": "not_checked",
        "data_access": access_policy.trace(),
        "model_routing": {
            "requested_model": requested_model_choice,
            "selected_model": effective_model_choice,
            "routed": False,
            "reason": "not_checked",
        },
        "token_budget": {
            "max_input_tokens": settings.max_input_tokens,
            "max_context_tokens": settings.max_context_tokens,
            "max_output_tokens": settings.max_output_tokens,
            "safe_query_tokens_est": safe_query_budget.original_tokens,
            "safe_query_trimmed": safe_query_budget.trimmed,
            "latest_question_tokens_est": latest_question_budget.original_tokens,
            "latest_question_trimmed": latest_question_budget.trimmed,
            "context_tokens_est": 0,
            "context_trimmed": False,
        },
        "language": language_context.trace(),
    }

    prompt_guardrail = validate_prompt(
        latest_question,
        settings.forbidden_topic_patterns,
        enabled=settings.prompt_validation_enabled,
    )
    trace["prompt_validation"] = "passed" if prompt_guardrail.allowed else "blocked"

    if not prompt_guardrail.allowed:
        trace["status"] = "blocked"
        trace["guardrail_reason"] = prompt_guardrail.reason
        emit_event(
            SAFE_COMPLETION,
            status="blocked",
            error=prompt_guardrail.reason,
            prompt_text=latest_question,
        )
        return _result(SAFE_COMPLETION, include_trace, trace)

    routing = select_model_for_query(latest_question, requested_model_choice, settings)
    effective_model_choice = routing.selected_model
    trace["model_choice"] = effective_model_choice
    trace["model_routing"] = routing.trace()

    if len(safe_query) > 1000:
        try:
            response = file_analyzer_tool(
                safe_query_for_model,
                effective_model_choice,
                max_output_tokens=settings.max_output_tokens,
                language_instructions=language_instructions,
            )
            output_guardrail = moderate_output(
                response,
                settings.output_moderation_patterns,
                enabled=settings.output_moderation_enabled,
            )
            trace["tool"] = "file"
            trace["output_moderation"] = "passed" if output_guardrail.allowed else "blocked"
            if not output_guardrail.allowed:
                response = SAFE_COMPLETION
                trace["status"] = "blocked"
                trace["guardrail_reason"] = output_guardrail.reason
                emit_event(
                    response,
                    status="blocked",
                    tool="file",
                    error=output_guardrail.reason,
                    prompt_text=safe_query,
                )
                return _result(response, include_trace, trace)

            trace["status"] = _status_for_response(response)
            emit_event(
                response,
                status=_status_for_response(response),
                tool="file",
                prompt_text=safe_query,
            )
            return _result(response, include_trace, trace)
        except Exception as e:
            response = f"Error: {str(e)}"
            trace["tool"] = "file"
            trace["status"] = "error"
            trace["error"] = str(e)
            emit_event(response, status="error", tool="file", error=str(e), prompt_text=safe_query)
            return _result(response, include_trace, trace)

    tool = decide_tool_llm(latest_question, effective_model_choice, temperature=0.0)
    trace["tool"] = tool

    if tool == "calculator":
        response = calculator_tool(latest_question)
        output_guardrail = moderate_output(
            response,
            settings.output_moderation_patterns,
            enabled=settings.output_moderation_enabled,
        )
        trace["output_moderation"] = "passed" if output_guardrail.allowed else "blocked"
        if not output_guardrail.allowed:
            response = SAFE_COMPLETION
            trace["status"] = "blocked"
            trace["guardrail_reason"] = output_guardrail.reason
            emit_event(
                response,
                status="blocked",
                tool="calculator",
                error=output_guardrail.reason,
                prompt_text=latest_question,
            )
            return _result(response, include_trace, trace)

        trace["status"] = _status_for_response(response)
        emit_event(
            response,
            status=_status_for_response(response),
            tool="calculator",
            prompt_text=latest_question,
        )
        return _result(response, include_trace, trace)

    retrieved_context = retrieve_context(
        latest_question,
        allowed_sources=access_policy.allowed_sources if access_policy.enabled else None,
    )
    context_text = format_context(retrieved_context)
    context_budget = trim_to_token_budget(context_text, settings.max_context_tokens)
    context_text = context_budget.text
    trace["token_budget"]["context_tokens_est"] = context_budget.original_tokens
    trace["token_budget"]["context_trimmed"] = context_budget.trimmed
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
    cache_key = answer_cache.make_key(
        latest_question,
        effective_model_choice,
        context_text,
        instruction_context=language_instructions,
    )
    messages = build_rag_answer_prompt(
        latest_question,
        context_text,
        language_instructions=language_instructions,
    )
    prompt_text = _messages_to_text(messages)
    cached_response = answer_cache.get(cache_key)

    if cached_response:
        reference_check = check_references(
            cached_response,
            retrieved_context,
            enabled=settings.reference_checking_enabled,
        )
        trace["reference_checking"] = "passed" if reference_check.passed else "fixed"
        if not reference_check.passed:
            cached_response = append_reference_notice(cached_response, retrieved_context)

        output_guardrail = moderate_output(
            cached_response,
            settings.output_moderation_patterns,
            enabled=settings.output_moderation_enabled,
        )
        trace["output_moderation"] = "passed" if output_guardrail.allowed else "blocked"
        if not output_guardrail.allowed:
            cached_response = SAFE_COMPLETION
            trace["status"] = "blocked"
            trace["guardrail_reason"] = output_guardrail.reason
            emit_event(
                cached_response,
                status="blocked",
                cache_hit=True,
                context_items=retrieved_context,
                error=output_guardrail.reason,
                prompt_text=prompt_text,
            )
            return _result(cached_response, include_trace, trace)

        trace["cache_hit"] = True
        trace["status"] = "ok"
        emit_event(
            cached_response,
            cache_hit=True,
            context_items=retrieved_context,
            prompt_text=prompt_text,
        )
        return _result(cached_response, include_trace, trace)

    try:
        response = chat_completion(
            messages,
            effective_model_choice,
            temperature=temperature,
            max_output_tokens=settings.max_output_tokens,
        )
        output_guardrail = moderate_output(
            response,
            settings.output_moderation_patterns,
            enabled=settings.output_moderation_enabled,
        )
        trace["output_moderation"] = "passed" if output_guardrail.allowed else "blocked"
        if not output_guardrail.allowed:
            response = SAFE_COMPLETION
            trace["status"] = "blocked"
            trace["guardrail_reason"] = output_guardrail.reason
            emit_event(
                response,
                status="blocked",
                context_items=retrieved_context,
                error=output_guardrail.reason,
                prompt_text=prompt_text,
            )
            return _result(response, include_trace, trace)

        reference_check = check_references(
            response,
            retrieved_context,
            enabled=settings.reference_checking_enabled,
        )
        trace["reference_checking"] = "passed" if reference_check.passed else "fixed"
        if not reference_check.passed:
            trace["reference_check_reason"] = reference_check.reason
            response = append_reference_notice(response, retrieved_context)

        status = _status_for_response(response)

        if status == "ok":
            answer_cache.set(cache_key, response)

        trace["status"] = status
        emit_event(response, status=status, context_items=retrieved_context, prompt_text=prompt_text)
        return _result(response, include_trace, trace)
    except Exception as e:
        response = f"Error: {str(e)}"
        trace["status"] = "error"
        trace["error"] = str(e)
        emit_event(
            response,
            status="error",
            context_items=retrieved_context,
            error=str(e),
            prompt_text=prompt_text,
        )
        return _result(response, include_trace, trace)


def answer_query_with_trace(
    query,
    model_choice="Llama",
    temperature=0.2,
    user_id="anonymous",
    user_context=None,
):
    return answer_query(
        query,
        model_choice=model_choice,
        include_trace=True,
        temperature=temperature,
        user_id=user_id,
        user_context=user_context,
    )
