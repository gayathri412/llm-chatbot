from prompts.system import SYSTEM_ROLE

def build_prompt(query):
    return [
        {"role": "system", "content": SYSTEM_ROLE},
        {"role": "user", "content": query}
    ]