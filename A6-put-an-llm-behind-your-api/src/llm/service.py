import hashlib
import json
import os
import random
import time
from pathlib import Path

from .provider import LLMTimeout, OpenAICompatibleProvider, ProviderFailure
from .schema import Classification

PROMPT_VERSION = "support-v1"
PROMPT_PATH = Path(__file__).parents[2] / "prompts" / "support-v1.md"
_CACHE: dict[str, Classification] = {}

class InvalidModelOutput(Exception):
    def __init__(self, raw: str, reason: str):
        super().__init__(reason)
        self.raw = raw
        self.reason = reason

class InputTooLarge(Exception):
    pass


def fallback(text: str) -> Classification:
    value = text.lower()
    if any(word in value for word in ("charge", "invoice", "payment", "refund")):
        return Classification(category="billing", urgency="high", confidence=0.9, reason="The message concerns a payment or charge.")
    if any(word in value for word in ("crash", "error", "broken", "bug", "fails")):
        return Classification(category="bug", urgency="high", confidence=0.9, reason="The message reports a product problem.")
    if any(word in value for word in ("add", "support", "feature", "would like")):
        return Classification(category="feature", urgency="normal", confidence=0.8, reason="The message requests product functionality.")
    return Classification(category="other", urgency="low", confidence=0.2, reason="The message is not clearly classifiable.")


def parse_classification(raw: str) -> Classification:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        parts = cleaned.split("\n", 1)
        cleaned = parts[1].rsplit("```", 1)[0].strip() if len(parts) == 2 else ""
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("model did not return a JSON object")
    return Classification.model_validate_json(cleaned[start:end + 1])


def _cost_log(response, repair_count: int) -> None:
    print(json.dumps({
        "prompt_version": PROMPT_VERSION,
        "model": os.getenv("LLM_MODEL", "gemma3:1b"),
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "duration_ms": response.duration_ms,
        "repair_count": repair_count,
    }, sort_keys=True))


def _call(provider, system_prompt: str, user_content: str, repair_count: int):
    for attempt in range(3):
        try:
            response = provider.complete(system_prompt, user_content)
            _cost_log(response, repair_count)
            return response
        except (LLMTimeout, ProviderFailure) as error:
            status = getattr(error, "status_code", None)
            retryable = isinstance(error, LLMTimeout) or status == 429 or (status is not None and status >= 500)
            if not retryable or attempt == 2:
                raise
            delay = getattr(error, "retry_after", None)
            if delay is None:
                delay = 2 ** attempt + random.uniform(0.11, 0.83)
            time.sleep(delay)
    raise RuntimeError("unreachable")


def classify(text: str, provider: OpenAICompatibleProvider | None = None) -> Classification:
    if os.getenv("LLM_ENABLED", "true").lower() == "false" or os.getenv("LLM_STUB") == "1":
        return fallback(text)
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    max_tokens = int(os.getenv("LLM_MAX_INPUT_TOKENS", "1200"))
    if (len(system_prompt) + len(text)) // 4 > max_tokens:
        raise InputTooLarge("input exceeds the configured token limit")
    key = hashlib.sha256(f"{PROMPT_VERSION}:{text}".encode()).hexdigest()
    if key in _CACHE:
        return _CACHE[key]
    provider = provider or OpenAICompatibleProvider()
    user_content = json.dumps({"text": text}, ensure_ascii=False)
    first = _call(provider, system_prompt, user_content, repair_count=0)
    try:
        result = parse_classification(first.content)
    except Exception as first_error:
        repair_content = (
            f"Original input: {user_content}\nBroken output: {first.content}\n"
            f"Validation error: {first_error}\n"
            "Your previous answer was rejected for this reason. Return only corrected JSON matching the schema."
        )
        repair = _call(provider, system_prompt, repair_content, repair_count=1)
        try:
            result = parse_classification(repair.content)
        except Exception as second_error:
            raise InvalidModelOutput(repair.content, str(second_error)) from second_error
    _CACHE[key] = result
    return result
