import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

DB_PATH = "tasks.db"


def init_db():
    """Create tasks.db, the tasks table, and seed three tasks only when empty."""
    conn = sqlite3.connect(DB_PATH)
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO tasks (title, done) VALUES (?, ?)",
                [
                    ("Buy milk", 0),
                    ("Call the dentist", 0),
                    ("Water the plants", 1),
                ],
            )
    conn.close()


init_db()

app = FastAPI(
    title="Task API",
    description="A small CRUD API that manages a to-do list, backed by SQLite. Try every endpoint here in Swagger UI.",
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


def row_to_task(row):
    """Convert a tasks.db row to the JSON shape the API has always returned."""
    return {"id": row[0], "title": row[1], "done": bool(row[2])}


@app.get("/")
async def root():
    """Describe the API and list its endpoints."""
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"],
    }


@app.get("/health")
async def health():
    """Return a simple liveness signal."""
    return {"status": "ok"}


@app.get("/tasks")
async def list_tasks(done: bool | None = None, search: str | None = None):
    """List tasks, optionally filtered by done status or a title search."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT * FROM tasks").fetchall()
    conn.close()
    result = [row_to_task(row) for row in rows]
    if done is not None:
        result = [t for t in result if t["done"] == done]
    if search is not None:
        needle = search.lower()
        result = [t for t in result if needle in t["title"].lower()]
    return result


@app.get("/tasks/{task_id}")
async def get_task(task_id: int):
    """Return a single task by its id, or 404 if it does not exist."""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    if row is None:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    return row_to_task(row)


@app.post("/tasks", status_code=201)
async def create_task(task_in: TaskIn):
    """Create a new task. The server assigns the id and sets done to false."""
    global next_id
    task = {"id": next_id, "title": task_in.title, "done": False}
    tasks.append(task)
    next_id += 1
    return task


@app.put("/tasks/{task_id}")
async def update_task(task_id: int, task_in: TaskUpdate):
    """Replace a task's title and/or done flag. Unknown ids return 404."""
    for task in tasks:
        if task["id"] == task_id:
            if task_in.title is not None:
                task["title"] = task_in.title
            if task_in.done is not None:
                task["done"] = task_in.done
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@app.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: int):
    """Remove a task. Unknown ids return 404."""
    for i, task in enumerate(tasks):
        if task["id"] == task_id:
            tasks.pop(i)
            return None
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@app.get("/stats")
async def stats():
    """Return a small summary the server computed from the list."""
    return {
        "total": len(tasks),
        "done": sum(1 for t in tasks if t["done"]),
        "open": sum(1 for t in tasks if not t["done"]),
    }


@app.post("/reset")
async def reset():
    """Restore the original three example tasks."""
    global next_id
    tasks[:] = [task.copy() for task in seed_tasks]
    next_id = len(tasks) + 1
    return {"status": "reset"}
