import os

from fastapi.testclient import TestClient

from .main import app

client = TestClient(app)

def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}

def test_stub_decision_is_closed_yes_no_set(monkeypatch):
    monkeypatch.setenv("AI_STUB", "1")
    response = client.post("/api/decide", json={"prompt": "Is this a support request?", "context": "I need help"})
    assert response.status_code == 200
    assert response.json()["decision"] in {"YES", "NO"}

def test_decision_requires_prompt():
    response = client.post("/api/decide", json={"context": "hello"})
    assert response.status_code == 422
