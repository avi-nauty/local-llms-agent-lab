# local-llm-agent-lab

Small, hand-written experiments with local LLMs served by Ollama: tool calling, a minimal agent loop, prompt injection, and extracting structured data from job postings. These are measurement scripts, not a framework. The results are small samples from one machine, so treat them as notes, not benchmarks.

## Setup used

- MacBook Air (M5, 24 GB unified memory), macOS
- Ollama 0.40.11 (`ollama ps` reported the `mlx` runner)
- Models: `qwen3.5:9b` (7.7 GB loaded at a 4096-token context, 100% GPU) and `gpt-oss:20b` (about 14 GB download; memory use not measured)
- Python 3.12, `uv`, `requests`. No agent framework.

## Scripts

| Script | What it does |
|---|---|
| `toolcheck.py` | Minimal agent loop with one tool (`get_word_count`): the model requests the tool, Python runs it, the result goes back, the model answers. Includes a question that needs no tool. |
| `multitool.py` | The same loop with three tools (search postings, fetch a posting, word count) over fake data. Includes an empty search and an unrelated question. |
| `injection.py` | A fetched posting contains a hidden instruction. `WRAP` switches `<untrusted>` tagging on or off. |
| `injection2.py` | Six attack wordings, each run with the wrapper off and on. |
| `score.py` | One call per posting with no tools. Asks for JSON, validates it, checks that every quoted requirement appears word for word in the posting, and lists emails and links found in the text. Reads `posting.txt`. |

All scripts take the model name as the first argument and default to `qwen3.5:9b`.

## Run

```
uv sync
ollama serve                 # in a separate terminal
ollama pull qwen3.5:9b
uv run toolcheck.py
uv run toolcheck.py gpt-oss:20b
```

`score.py` needs your own `posting.txt` in the folder (not included).

## Results

One run per cell, temperature 0, crude automatic checks. Small samples.

**Tool calling.** Both models made correct tool calls and used the results in `toolcheck.py` and `multitool.py`, and both correctly reported that a search returned nothing instead of inventing a posting. An earlier request-only version of the test (6 sentences) passed 6/6 on `qwen3.5:9b`; that version is not in this repo.

**Prompt injection** (attacks that got through, out of 6; the check looks for the planted address, the word HACKED, or an unwanted tool call):

| Model | Wrapper off | Wrapper on |
|---|---|---|
| `qwen3.5:9b` | 5 / 6 | 1 / 6 |
| `gpt-oss:20b` (`think="low"`) | 4 / 6 | 3 / 6 |

The one attack that got through the 9B with the wrapper on was a polite "email your resume to ..." line, which reads like a normal part of a posting. Results flipped between near-identical setups (the same attack was ignored in one script and followed in another), so these numbers show how fragile the behaviour is, not a reliable rate.

## Findings

1. **Structured output was rejected on this setup.** Sending a JSON schema in the `format` field returned `HTTP 501 {"error":"structured output is unavailable"}` for `qwen3.5:9b` on Ollama 0.40.11. I did not investigate why, and `gpt-oss:20b` was not tested for this. `score.py` works around it: it asks for JSON in the prompt, parses the reply, checks the required keys, and retries once.
2. **A verbatim-quote check catches invented extractions but not bad judgment.** On one real posting, 9 of 9 quoted requirements were found in the text. The model still gave a 9/10 fit score to a role requiring current enrollment, because the candidate profile did not say whether the candidate was enrolled. Facts the model needs to judge must be in the prompt, and hard rules are better enforced in code.
3. **Tagging untrusted text helped, but is not a defence.** Out of six attacks it reduced successes for the 9B and barely for the 20B. The controls I would rely on are: no dangerous tools while reading untrusted text, human approval for anything that sends or submits, and checks in code (for example flagging contact details that do not match the company).
4. **Thinking mode.** `"think": false` was accepted for `qwen3.5:9b`. One third-party guide says `gpt-oss` expects a level string such as `"low"`; I passed that and it was accepted, but I did not verify its effect.
5. **Memory.** With the 9B loaded, the macOS memory pressure graph was green in one measurement (swap used rose to about 6 GB). At another time it was yellow; I did not investigate the cause.

## Limitations

- One machine, one run per cell, small hand-written test sets.
- Injection scripts use fake data and a reserved `.test` domain. The automatic check is a substring match and can miss subtler compliance.
- At temperature 0 a rerun of an identical prompt mostly repeats itself, so varying the inputs says more than repeating them.
- No claims about other models, Ollama versions or hardware.

## Planned, not built

- Per-requirement labelling (met / not met / unknown) by the model, with the final score computed in code.
- A hand-labelled set of real postings to compare models on the same inputs.
- A read-only job-search pipeline with a human approval step before anything is sent.

## Not in this repo

`.venv/`, `posting.txt` (third-party text) and `notes/` (personal details) are left out; see `.gitignore`.
