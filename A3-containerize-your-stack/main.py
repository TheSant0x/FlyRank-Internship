from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import repository

repository.init_db()

try:
    repository.ping_redis()
except Exception:
    # Redis is a stretch extra; the API still starts without it.
    pass

app = FastAPI(
    title="Task API",
    description="A small CRUD API that manages a to-do list, backed by Postgres in Docker.",
    version="1.0",
)


@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": "title is required and must not be empty"},
    )


class TaskIn(BaseModel):
    title: str = Field(min_length=1, description="Task title, must not be empty")


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    done: bool | None = None


@app.get("/")
async def root():
    """Describe the API and list its endpoints."""
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health")
async def health():
    """Liveness signal that also pings the database."""
    try:
        repository.ping_db()
        return {"status": "ok", "db": "ok"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "error", "db": "down"})


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


@app.post("/tasks", status_code=201)
async def create_task(task_in: TaskIn):
    """Create a new task. The server assigns the id and sets done to false."""
    return repository.create_task(task_in.title)


@app.put("/tasks/{task_id}")
async def update_task(task_id: int, task_in: TaskUpdate):
    """Replace a task's title and/or done flag. Unknown ids return 404."""
    if task_in.title is None and task_in.done is None:
        return JSONResponse(
            status_code=400,
            content={"error": "title or done is required"},
        )
    task = repository.update_task(
        task_id, title=task_in.title, done=task_in.done
    )
    if task is None:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    return task


@app.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: int):
    """Remove a task. Unknown ids return 404."""
    if not repository.delete_task(task_id):
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    return None


@app.get("/stats")
async def stats():
    """Return counts computed by SQL, not by counting rows in code."""
    return repository.stats()


@app.post("/reset")
async def reset():
    """Restore the original three example tasks."""
    repository.reset()
    return {"status": "reset"}
