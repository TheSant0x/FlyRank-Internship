"""AI-generated comparison implementation, kept separate from the reviewed app."""
import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .llm.provider import LLMTimeout, ProviderFailure
from .llm.schema import Classification, SupportInput
from .llm.service import InputTooLarge, InvalidModelOutput, classify

app = FastAPI(title="Support Triage API (AI comparison)", version="1.0.0")

@app.exception_handler(RequestValidationError)
async def request_validation_error(request: Request, error: RequestValidationError):
    field = str(error.errors()[0].get("loc", ["text"])[-1]) if error.errors() else "text"
    return JSONResponse(status_code=400, content={"message": f"Invalid field: {field}"})

@app.post("/triage", response_model=Classification)
async def triage(payload: SupportInput):
    try:
        return classify(payload.text)
    except InputTooLarge as error:
        return JSONResponse(status_code=400, content={"message": f"Invalid field: text ({error})"})
    except LLMTimeout:
        return JSONResponse(status_code=504, content={"message": "LLM request timed out"})
    except InvalidModelOutput as error:
        Path("logs").mkdir(exist_ok=True)
        with Path("logs/quarantine.jsonl").open("a", encoding="utf-8") as log:
            log.write(json.dumps({"input": payload.text, "error": error.reason, "raw_output": error.raw, "prompt_version": "support-v1"}) + "\n")
        return JSONResponse(status_code=422, content={"message": "Model output could not be validated"})
    except ProviderFailure as error:
        return JSONResponse(status_code=502, content={"message": f"LLM provider error (HTTP {error.status_code or 'unknown'})"})
