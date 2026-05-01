NO_CONTEXT_MESSAGE = "No relevant local context found."

RAG_ANSWER_PROMPT = """Answer the user's question clearly and accurately.

Instructions:
- First use the retrieved context when it is relevant
- If the context does not contain the answer, say that clearly and then use general knowledge
- Do not invent facts that are not supported by the context
- Keep explanation simple and clear

User Question:
{user_query}

Retrieved Context:
{context}

Answer:"""

BIGDATA_ANALYSIS_PROMPT = """SQL Query:
{sql_query}

Results Summary:
{results_summary}

User Question:
{user_query}

Provide analysis:"""

SQL_EXPLANATION_PROMPT = """Explain this SQL query:
{sql_query}"""


def format_context_snippets(context_snippets: list[str], limit: int = 10) -> str:
    return "\n\n".join(context_snippets[:limit]) if context_snippets else NO_CONTEXT_MESSAGE
