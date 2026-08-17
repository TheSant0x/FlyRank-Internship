import os

from src.llm.provider import LLMTimeout, ProviderFailure
from src.llm.service import classify, clear_cache

class Response:
    input_tokens = 3
    output_tokens = 2
    duration_ms = 1
    def __init__(self, content):
        self.content = content

VALID = '{"category":"other","urgency":"low","confidence":0.2,"reason":"Not enough information."}'

class SequenceProvider:
    def __init__(self, values):
        self.values = iter(values)
        self.calls = 0
    def complete(self, *_):
        self.calls += 1
        value = next(self.values)
        if isinstance(value, Exception):
            raise value
        return Response(value)

def test_retryable_timeout_is_retried(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.delenv("LLM_STUB", raising=False)
    monkeypatch.setattr("src.llm.service.time.sleep", lambda _: None)
    clear_cache()
    provider = SequenceProvider([LLMTimeout("slow"), VALID])
    assert classify("timeout retry", provider).category.value == "other"
    assert provider.calls == 2

def test_auth_failure_is_not_retried(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.delenv("LLM_STUB", raising=False)
    clear_cache()
    provider = SequenceProvider([ProviderFailure("bad key", status_code=401), VALID])
    try:
        classify("auth failure", provider)
    except ProviderFailure:
        pass
    else:
        raise AssertionError("expected ProviderFailure")
    assert provider.calls == 1

def test_cache_includes_prompt_and_avoids_second_call(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.delenv("LLM_STUB", raising=False)
    clear_cache()
    provider = SequenceProvider([VALID])
    classify("same input", provider)
    classify("same input", provider)
    assert provider.calls == 1
