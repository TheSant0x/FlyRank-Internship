from .schema import Classification


def fallback(text: str) -> Classification:
    value = text.lower()
    if any(word in value for word in ("charge", "invoice", "payment", "refund")):
        return Classification(category="billing", urgency="high", confidence=0.9, reason="The message concerns a payment or charge.")
    if any(word in value for word in ("crash", "error", "broken", "bug", "fails")):
        return Classification(category="bug", urgency="high", confidence=0.9, reason="The message reports a product problem.")
    if any(word in value for word in ("add", "support", "feature", "would like")):
        return Classification(category="feature", urgency="normal", confidence=0.8, reason="The message requests product functionality.")
    return Classification(category="other", urgency="low", confidence=0.2, reason="The message is not clearly classifiable.")


def classify(text: str) -> Classification:
    return fallback(text)
