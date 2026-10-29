import json
import requests
import sys

MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen3.5:9b"
THINK = "low" if "gpt-oss" in MODEL else False

URL = "http://localhost:11434/api/chat"
MAX_STEPS = 8

POSTINGS = {
    1: {"title": "Junior ML Engineer", "company": "Acme Health",
        "text": "Acme Health seeks a Junior ML Engineer. Requires Python, "
                "PyTorch, 0-2 years experience. Location: Kitchener, ON."},
    2: {"title": "Senior DevOps Lead", "company": "BigCorp",
        "text": "BigCorp needs a Senior DevOps Lead with 8+ years experience, "
                "Kubernetes, Terraform. Location: Toronto, ON."},
    3: {"title": "Data Engineer", "company": "Northwind Analytics",
        "text": "Build ETL pipelines. Requires SQL, Python, Airflow, "
                "1-3 years. Location: Waterloo, ON."},
}


def search_postings(query: str) -> str:
    words = query.lower().split()
    hits = [{"id": i, "title": p["title"], "company": p["company"]}
            for i, p in POSTINGS.items()
            if any(w in p["title"].lower() for w in words)]
    return json.dumps(hits)


def fetch_posting(posting_id) -> str:
    p = POSTINGS.get(int(posting_id))
    if p is None:
        return "ERROR: no posting with that id"
    return p["text"]


def get_word_count(text: str) -> int:
    return len(text.split())


TOOL_FUNCTIONS = {
    "search_postings": search_postings,
    "fetch_posting": fetch_posting,
    "get_word_count": get_word_count,
}


def tool_schema(name, description, props, required):
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": props,
                       "required": required}}}


tools = [
    tool_schema("search_postings",
                "Find job postings whose title matches the query. "
                "Returns a list of ids, titles and companies.",
                {"query": {"type": "string"}}, ["query"]),
    tool_schema("fetch_posting",
                "Get the full text of one job posting by its id.",
                {"posting_id": {"type": "integer"}}, ["posting_id"]),
    tool_schema("get_word_count",
                "Count the words in a piece of text.",
                {"text": {"type": "string"}}, ["text"]),
]


def ask(question):
    messages = [
        {"role": "system", "content":
         "You help with job postings. Only state facts that appear in tool "
         "results. If a tool finds nothing, say so."},
        {"role": "user", "content": question},
    ]
    for step in range(MAX_STEPS):
        r = requests.post(URL, json={
            "model": MODEL, "messages": messages, "tools": tools,
            "stream": False, "think": False,
            "options": {"temperature": 0, "num_ctx": 4096},
        }, timeout=300)
        r.raise_for_status()
        msg = r.json()["message"]
        messages.append(msg)

        calls = msg.get("tool_calls") or []
        if not calls:
            return msg.get("content", ""), step + 1

        for call in calls:
            name = call["function"]["name"]
            args = call["function"]["arguments"]
            if isinstance(args, str):
                args = json.loads(args)
            try:
                result = TOOL_FUNCTIONS[name](**args)
            except Exception as e:
                result = f"ERROR: {e}"
            print(f"  tool call: {name}({args}) -> {str(result)[:100]}")
            messages.append({"role": "tool", "tool_name": name,
                             "content": str(result)})
    return "(hit step limit)", MAX_STEPS


QUESTIONS = [
    "Which posting is for a junior ML engineer, and what does it require?",
    "Is there a posting for a Rust developer?",
    "How many words are in: 'a b c'?",
]

for q in QUESTIONS:
    print(f"\nQ: {q}")
    answer, calls_made = ask(q)
    print(f"A: {answer}  [model calls: {calls_made}]")