from prompts.formatters import NO_CONTEXT_MESSAGE, format_context_snippets
from prompts.manager import prompt_manager

def build_prompt(query):
    return prompt_manager.compose("basic", query=query)

def build_prompt_with_context(user_query: str, context_snippets: list[str]) -> list[dict]:
    context = format_context_snippets(context_snippets)
    return build_rag_answer_prompt(user_query, context)

def build_bigdata_analysis_prompt(user_query: str, sql_query: str, results_summary: str) -> list[dict]:
    return prompt_manager.compose(
        "bigdata_analysis",
        user_query=user_query,
        sql_query=sql_query,
        results_summary=results_summary,
    )

def build_sql_explanation_prompt(sql_query: str) -> list[dict]:
    return prompt_manager.compose("sql_explanation", sql_query=sql_query)

def build_tool_selection_prompt(query: str) -> list[dict]:
    return prompt_manager.compose("tool_selector", query=query)

def build_rag_answer_prompt(user_query: str, context: str) -> list[dict]:
    return prompt_manager.compose(
        "rag_answer",
        user_query=user_query,
        context=context or NO_CONTEXT_MESSAGE,
    )

def list_prompt_templates() -> list[str]:
    return prompt_manager.available_templates()
