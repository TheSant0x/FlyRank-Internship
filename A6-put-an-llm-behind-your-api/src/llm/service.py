import json
import os
from pathlib import Path

from .provider import LLMTimeout, OpenAICompatibleProvider, ProviderFailure
from .schema import Classification

PROMPT_VERSION = "support-v1"
PROMPT_PATH = Path(__file__).parents[2] / "prompts" / "support-v1.md"


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
        cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("model did not return a JSON object")
    return Classification.model_validate_json(cleaned[start:end + 1])


def classify(text: str, provider: OpenAICompatibleProvider | None = None) -> Classification:
    if os.getenv("LLM_STUB") == "1":
        return fallback(text)
    provider = provider or OpenAICompatibleProvider()
    response = provider.complete(PROMPT_PATH.read_text(encoding="utf-8"), json.dumps({"text": text}))
    return parse_classification(response.content)
