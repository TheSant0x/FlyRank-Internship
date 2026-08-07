FROM python:3.13-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN python -m venv /venv && \
    /venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.13-slim

WORKDIR /app

COPY --from=builder /venv /venv
COPY . .

ENV PATH="/venv/bin:$PATH"

EXPOSE 3000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000"]
