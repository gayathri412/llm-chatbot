# app/tools.py

def calculator_tool(query: str):
    try:
        result = eval(query)
        return f"🧮 Result: {result}"
    except:
        return "⚠️ Invalid calculation"


def file_analyzer_tool(text: str):
    return f"📄 Summary:\n{text[:300]}..."