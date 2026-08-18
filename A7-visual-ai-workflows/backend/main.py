from fastapi import FastAPI

app = FastAPI(title="Branchline AI Decision Service", version="1.0.0")

@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
