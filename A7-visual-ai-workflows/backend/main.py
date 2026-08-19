import os
import re
from enum import Enum

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

load_dotenv()

app = FastAPI(title="Branchline AI Decision Service", version="1.0.0")

class Decision(str, Enum):
    YES = "YES"
    NO = "NO"

class DecisionRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    context: str = Field(default="", max_length=6000)

class DecisionResponse(BaseModel):
    decision: Decision
    model: str

@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.post("/api/decide", response_model=DecisionResponse)
def decide(request: DecisionRequest) -> DecisionResponse:
    if os.getenv("AI_STUB", "1") == "1":
        text = f"{request.prompt} {request.context}".lower()
        positive = ("support", "urgent", "help", "problem", "bug", "yes")
        answer = Decision.YES if any(word in text for word in positive) else Decision.NO
        return DecisionResponse(decision=answer, model="stub")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured")
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            timeout=30.0,
            max_retries=0,
        )
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
            max_tokens=2,
            messages=[
                {"role": "system", "content": "Answer every decision with exactly YES or NO. Do not add punctuation or explanation."},
                {"role": "user", "content": f"Question: {request.prompt}\nContext: {request.context}"},
            ],
        )
        content = re.sub(r"[^A-Z]", "", (response.choices[0].message.content or "").upper())
        if content not in {Decision.YES.value, Decision.NO.value}:
            raise ValueError("model did not return exactly YES or NO")
        return DecisionResponse(decision=Decision(content), model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"AI decision failed: {error}") from error
