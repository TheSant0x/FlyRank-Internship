from fastapi import FastAPI

app = FastAPI(title="FlyRank PDF Report Generator", version="1.0.0")

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
