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
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "INSERT INTO tasks (title, done) VALUES (?, ?)",
        (task_in.title, 0),
    )
    conn.commit()
    task_id = cur.lastrowid
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    task = row_to_task(row)
    return task


@app.put("/tasks/{task_id}")
async def update_task(task_id: int, task_in: TaskUpdate):
    """Replace a task's title and/or done flag. Unknown ids return 404."""
    new_title = task_in.title if task_in.title is not None else None
    new_done = task_in.done if task_in.done is not None else None
    conn = sqlite3.connect(DB_PATH)
    if new_title is not None and new_done is not None:
        conn.execute(
            "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
            (new_title, int(new_done), task_id),
        )
    elif new_title is not None:
        conn.execute("UPDATE tasks SET title = ? WHERE id = ?", (new_title, task_id))
    elif new_done is not None:
        conn.execute("UPDATE tasks SET done = ? WHERE id = ?", (int(new_done), task_id))
    else:
        conn.close()
        return JSONResponse(status_code=400, content={"error": "title or done is required"})
    conn.commit()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    if row is None:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    return row_to_task(row)


@app.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: int):
    """Remove a task. Unknown ids return 404."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    return None


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
