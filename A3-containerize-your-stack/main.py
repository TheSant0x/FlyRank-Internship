from fastapi import FastAPI

import repository

repository.init_db()

app = FastAPI(
    title="Task API",
    description="A small CRUD API that manages a to-do list, backed by Postgres in Docker.",
    version="1.0",
)


@app.get("/")
async def root():
    """Describe the API and list its endpoints."""
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}
