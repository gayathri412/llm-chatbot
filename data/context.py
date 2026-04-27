import json

def load_docs():
    with open("data/docs.json", "r") as f:
        return json.load(f)

def fetch_context(query, limit=3):
    docs = load_docs()
    results = []

    for doc in docs:
        if query.lower() in doc["body"].lower() or query.lower() in doc["title"].lower():
            results.append(doc["body"])

    return results[:limit]