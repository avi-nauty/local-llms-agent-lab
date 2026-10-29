import json
import requests
import sys

MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen3.5:9b"
THINK = "low" if "gpt-oss" in MODEL else False


URL = "http://localhost:11434/api/chat"
MAX_STEPS = 5


def get_word_count(text: str) -> int:
    return len(text.split())


# Maps the tool's name (what the model asks for) to the real function.
TOOL_FUNCTIONS = {"get_word_count": get_word_count}

tools = [{
    "type": "function",
    "function": {
        "name": "get_word_count",
        "description": "Count the words in a piece of text.",
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
}]


def ask(question):
    messages = [{"role": "user", "content": question}]

    for step in range(MAX_STEPS):
        r = requests.post(URL, json={
            "model": MODEL,
            "messages": messages,
            "tools": tools,
            "stream": False,
            "think": THINK,
            "options": {"temperature": 0, "num_ctx": 4096},
        }, timeout=300)
        r.raise_for_status()
        msg = r.json()["message"]
        messages.append(msg)

        calls = msg.get("tool_calls") or []
        if not calls:
            return msg.get("content", ""), step

        for call in calls:
            name = call["function"]["name"]
            args = call["function"]["arguments"]
            if isinstance(args, str):
                args = json.loads(args)
            try:
                result = TOOL_FUNCTIONS[name](**args)
            except Exception as e:
                result = f"ERROR: {e}"
            print(f"  tool call: {name}({args}) -> {result}")
            messages.append({
                "role": "tool",
                "tool_name": name,
                "content": str(result),
            })

    return "(hit step limit without a final answer)", MAX_STEPS


QUESTIONS = [
    "How many words are in: 'the quick brown fox jumps'?",
    "How many words are in: 'to be or not to be that is the question'?",
    "What is the capital of France?",
]

for q in QUESTIONS:
    print(f"\nQ: {q}")
    answer, steps = ask(q)
    print(f"A: {answer}  [model calls: {steps + 1}]")