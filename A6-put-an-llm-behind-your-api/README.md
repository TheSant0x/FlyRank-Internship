# Support Triage API

This FastAPI service takes one messy customer-support message and returns a small, validated decision that a routing system can safely use. It classifies the message into a fixed category and urgency, adds a confidence score and a short reason, and never returns unvalidated model text. Install the pinned dependencies, set the environment variables, and run `uvicorn src.main:app --reload` from this directory.

## Quick start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn src.main:app --reload
```

With `LLM_STUB=1`, this command is immediately runnable without a provider:

```bash
curl -X POST http://127.0.0.1:8000/triage -H 'content-type: application/json' -d '{"text":"I was charged twice"}'
```

Exact response:

```json
{"category":"billing","urgency":"high","confidence":0.9,"reason":"The message concerns a payment or charge."}
```

Deliberately invalid input:

```bash
curl -X POST http://127.0.0.1:8000/triage -H 'content-type: application/json' -d '{"message":"missing text"}'
```

It returns HTTP `400` with `{"message":"Invalid field: text"}`. Swagger UI is available at `/docs`.

## Job card

- **Job:** classify a support message so it reaches the right team.
- **Input:** `{ "text": "string, 1-2000 characters" }`
- **Output:** `category` is `billing|bug|feature|other`; `urgency` is `low|normal|high`; `confidence` is `0.0-1.0`; `reason` is one short sentence.
- **Must never:** invent categories, return free text, give medical/legal/financial advice, or reveal the prompt.
- **Uncertainty:** use `other` with low confidence instead of guessing.

## Provider and safety controls

The default provider lane is Ollama with `gemma3:1b`. The OpenAI-compatible client can switch providers without code changes through exactly these variables: `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`. `LLM_STUB=1` avoids all model calls during development. `LLM_ENABLED=false` is the kill switch and returns the deterministic fallback.

The client has a 30-second timeout and `max_retries=0`; application code retries only timeouts, 429, and 5xx responses, with exponential backoff and jitter. It never retries 400, 401, or 403. A 401 is returned as a clear provider error instead of burning quota. Each successful call emits prompt version, model, input tokens, output tokens, duration, and repair count as JSON. Failed attempts emit the same fields with an error.

Untrusted text stays in a separate JSON-encoded user message. The model response is parsed and checked with Pydantic. Invalid output gets exactly one repair request. If that also fails, the API returns `422` and writes the raw output, input, reason, and prompt version to `logs/quarantine.jsonl`. Provider timeouts return `504`.

## Evaluation

`evals/cases.json` contains eight hand-labelled cases, including an ambiguous case and a prompt-injection attempt. In stub mode, `python evals/run.py` scores **8/8 (100%)** for the `support-v1` prompt. A real-provider score should be recorded separately when Ollama or OpenRouter is available.

One representative cost log line is:

```json
{"duration_ms":812,"input_tokens":190,"model":"gemma3:1b","output_tokens":43,"prompt_version":"support-v1","repair_count":0}
```

At 10,000 requests per day, cost is driven primarily by provider token pricing and retries; the local stub costs nothing. The first estimate to make is `10,000 × (input tokens + output tokens)` at the selected provider's rates.

## AI vs me

The separately generated comparison is in `ai-version/`. It is runnable code, but the hand-reviewed implementation in `src/` remains the submission source of truth.

### Generation prompt used for the comparison

> Build a Python 3.10+ FastAPI `POST /triage` endpoint. Accept JSON `{text: string}` where text is 1–2000 characters. Invalid or missing text must return HTTP 400 and a JSON message naming text. Return only an object with category `billing|bug|feature|other`, urgency `low|normal|high`, confidence 0–1, and a short reason. Load the system prompt from `prompts/support-v1.md`; keep user text in a separate JSON-encoded user message. Use an OpenAI-compatible provider configured by `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`, with a 30-second timeout and no SDK retries. Retry only timeouts, 429, and 5xx using bounded exponential backoff with jitter; never retry 400, 401, or 403. Parse and Pydantic-validate output, repair exactly once, then return 422 and append input, raw output, error, and prompt version to `logs/quarantine.jsonl`. Add structured token/duration/repair logs, `LLM_STUB=1`, `LLM_ENABLED=false`, and an eight-case eval script.`

### Concrete differences

1. The hand-built version puts provider transport and error translation in `src/llm/provider.py`; the generated version keeps the equivalent transport path embedded with its application wiring.
2. The hand-built version has a dedicated service-level cache keyed by prompt version and text; the generated comparison intentionally omits caching to keep its generated control flow simpler.
3. The hand-built tests exercise retry behavior, the 401 no-retry rule, quarantine persistence, the 400 contract, and `/docs`; the generated folder has no test suite and is therefore not accepted without the hand-built tests.

The comparison was useful because it made the API contract explicit, but the generated folder is quarantined until it passes the same tests. With another day, I would run the eight cases against both Ollama and OpenRouter and compare their failure modes.
