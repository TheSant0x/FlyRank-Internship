import os
import time
from dataclasses import dataclass

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

@dataclass(frozen=True)
class ModelResponse:
    content: str
    input_tokens: int
    output_tokens: int
    duration_ms: int
    retry_after: float | None = None

class LLMTimeout(Exception):
    pass

class ProviderFailure(Exception):
    def __init__(self, message: str, status_code: int | None = None, retry_after: float | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after

class OpenAICompatibleProvider:
    def __init__(self) -> None:
        self.model = os.environ.get("LLM_MODEL", "gemma3:1b")
        self.client = OpenAI(
            base_url=os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1/"),
            api_key=os.environ.get("LLM_API_KEY", "ollama"),
            timeout=30.0,
            max_retries=0,
        )

    def complete(self, system_prompt: str, user_content: str) -> ModelResponse:
        started = time.monotonic()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.2,
            )
        except Exception as error:
            status = getattr(error, "status_code", None)
            headers = getattr(error, "response", None)
            headers = getattr(headers, "headers", {}) or {}
            retry_after = _retry_after(headers.get("retry-after"))
            if error.__class__.__name__ in {"APITimeoutError", "APITimeoutError"}:
                raise LLMTimeout("LLM request timed out") from error
            raise ProviderFailure(str(error), status, retry_after) from error
        usage = response.usage
        return ModelResponse(
            content=response.choices[0].message.content or "",
            input_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
            output_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
            duration_ms=round((time.monotonic() - started) * 1000),
        )

def _retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None
