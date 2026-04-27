from app.orchestrator import answer_query

while True:
    query = input("Ask something (type exit to quit): ")
    if query.lower() == "exit":
        break
    print(answer_query(query))