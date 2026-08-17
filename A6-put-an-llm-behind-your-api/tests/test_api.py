import json

import httpx
import pytest
from httpx import ASGITransport

from src import main
from src.llm.provider import LLMTimeout, ProviderFailure
from src.llm.schema import Classification
from src.llm.service import clear_cache

@pytest.fixture
def client():
    return httpx.AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test")

@pytest.mark.anyio
async def test_valid_stub_response_and_docs(client, monkeypatch):
    monkeypatch.setenv("LLM_STUB", "1")
    response = await client.post("/triage", json={"text": "I was charged twice"})
    assert response.status_code == 200
    assert set(response.json()) == {"category", "urgency", "confidence", "reason"}
    docs = await client.get("/docs")
    assert docs.status_code == 200 and "Swagger UI" in docs.text
    await client.aclose()

@pytest.mark.anyio
@pytest.mark.parametrize("body", [{}, {"text": 4}, {"text": ""}, {"text": "x" * 2001}])
async def test_bad_input_is_400_and_names_text(client, body, monkeypatch):
    monkeypatch.setenv("LLM_STUB", "1")
    response = await client.post("/triage", json=body)
    assert response.status_code == 400
    assert "text" in response.json()["message"]
    await client.aclose()

@pytest.mark.anyio
async def test_unrepairable_model_output_is_422_and_quarantined(client, monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.delenv("LLM_STUB", raising=False)
    clear_cache()
    class BadProvider:
        calls = 0
        def complete(self, *_):
            self.calls += 1
            return type("Response", (), {"content": "not json", "input_tokens": 1, "output_tokens": 1, "duration_ms": 1})()
    provider = BadProvider()
    monkeypatch.setattr(main, "classify", lambda text: (_ for _ in ()).throw(Exception("not wired")))
    # The route's public behavior is tested with its actual exception type.
    from src.llm.service import InvalidModelOutput
    monkeypatch.setattr(main, "classify", lambda text: (_ for _ in ()).throw(InvalidModelOutput("bad", "invalid JSON")))
    monkeypatch.chdir(tmp_path)
    response = await client.post("/triage", json={"text": "hello"})
    assert response.status_code == 422
    line = json.loads((tmp_path / "logs" / "quarantine.jsonl").read_text())
    assert line["raw_output"] == "bad" and line["prompt_version"] == "support-v1"
    await client.aclose()

@pytest.mark.anyio
async def test_timeout_is_504(client, monkeypatch):
    monkeypatch.setattr(main, "classify", lambda text: (_ for _ in ()).throw(LLMTimeout("slow")))
    response = await client.post("/triage", json={"text": "hello"})
    assert response.status_code == 504
    await client.aclose()
