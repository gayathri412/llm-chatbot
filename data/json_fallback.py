import json

def fetch_context(query):
    try:
        with open("data/sample.json") as f:
            data = json.load(f)

        results = []

        for item in data:
            if query.lower() in item["body"].lower():
                results.append(item["body"])

        return results[:3]

    except:
        return []