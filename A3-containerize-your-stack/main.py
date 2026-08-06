from fastapi import FastAPI
from fastapi.responses import JSONResponse

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


@app.get("/tasks")
async def list_tasks(
    done: bool | None = None,
    search: str | None = None,
    sort: str | None = None,
):
    """List tasks straight from Postgres, with the same filters as A2."""
    return repository.list_tasks(done=done, search=search, sort=sort)


@app.get("/tasks/{task_id}")
async def get_task(task_id: int):
    """Return a single task by its id, or 404 if it does not exist."""
    task = repository.get_task(task_id)
    if task is None:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    return task
