# prompts/assistant.py
RESPONSE_STYLE = """Use bullet points for steps, keep answers under 200 words unless asked for more.
When you use retrieved context, include at least one reference marker like [1] or the title/source.
"""

BIGDATA_ANALYSIS_STYLE = """Analyze the data results and provide:
1. Key insights and patterns
2. Trends observed
3. Recommendations based on data
4. Any anomalies or outliers
Use bullet points and be specific with numbers.
"""

SQL_EXPLANATION_STYLE = """Explain the SQL query in simple terms:
1. What the query does
2. Key operations (JOINs, filters, aggregations)
3. Expected output
Keep it concise and beginner-friendly.
"""
