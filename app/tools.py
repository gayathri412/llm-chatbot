from llm.client import chat_completion

def file_analyzer_tool(text: str, model_choice="Llama"):

    prompt = f"""
You are an AI document analyst.

Analyze the following document and provide:

1. Summary
2. Key Points
3. Important Insights

Document:
{text[:3000]}

Give a clear and structured answer.
"""

    messages = [
        {"role": "system", "content": "You are a document analysis expert."},
        {"role": "user", "content": prompt}
    ]

    response = chat_completion(messages, model_choice)

    return response