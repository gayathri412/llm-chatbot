# prompts/compose.py
from prompts.system import SYSTEM_ROLE
from prompts.assistant import RESPONSE_STYLE, BIGDATA_ANALYSIS_STYLE, SQL_EXPLANATION_STYLE

def build_prompt(query):
    """Basic prompt builder"""
    return [
        {"role": "system", "content": SYSTEM_ROLE},
        {"role": "user", "content": query}
    ]

def build_prompt_with_context(user_query: str, context_snippets: list[str]) -> list[dict]:
    """Build prompt with context snippets for RAG"""
    system = {"role": "system", "content": SYSTEM_ROLE + "\n" + RESPONSE_STYLE}
    context = "\n\n".join(context_snippets[:10]) if context_snippets else "No additional context."
    user = {
        "role": "user",
        "content": f"User query: {user_query}\n\nRelevant context:\n{context}\n\nAnswer:"
    }
    return [system, user]

def build_bigdata_analysis_prompt(user_query: str, sql_query: str, results_summary: str) -> list[dict]:
    """Build prompt for Big Data analysis"""
    system = {"role": "system", "content": SYSTEM_ROLE + "\n" + BIGDATA_ANALYSIS_STYLE}
    user = {
        "role": "user",
        "content": f"SQL Query: {sql_query}\n\nResults Summary:\n{results_summary}\n\nUser Question: {user_query}\n\nProvide analysis:"
    }
    return [system, user]

def build_sql_explanation_prompt(sql_query: str) -> list[dict]:
    """Build prompt to explain SQL query"""
    system = {"role": "system", "content": SYSTEM_ROLE + "\n" + SQL_EXPLANATION_STYLE}
    user = {
        "role": "user",
        "content": f"Explain this SQL query:\n{sql_query}"
    }
    return [system, user]