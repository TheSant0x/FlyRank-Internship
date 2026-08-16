import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .llm.schema import SupportInput
from .llm.service import classify

app = FastAPI(title="Support Triage API", version="1.0.0")


def invalid_field(error: Exception) -> str:
    if isinstance(error, ValidationError) and error.errors():
        return str(error.errors()[0]["loc"][-1])
    return "text"


@app.post("/triage", status_code=200)
async def triage(request: Request):
    try:
        payload = SupportInput.model_validate(await request.json())
    except (ValidationError, TypeError, ValueError) as error:
        return JSONResponse(status_code=400, content={"message": f"Invalid field: {invalid_field(error)}"})

    try:
        return classify(payload.text).model_dump(mode="json")
    except Exception:
        return JSONResponse(status_code=422, content={"message": "Model output could not be validated"})
