import sqlite3
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

DB_PATH = "tasks.db"

SEED_TASKS = [
    ("Buy milk", 0),
    ("Call the dentist", 0),
    ("Water the plants", 1),
]


def init_db():
    """Create tasks.db and the tasks table, then seed three tasks only when empty."""
    conn = sqlite3.connect(DB_PATH)
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        # Small migration: add the timestamp columns to databases created before
        # the extras existed, so an older tasks.db keeps working.
        columns = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
        if "created_at" not in columns:
            conn.execute(
                "ALTER TABLE tasks ADD COLUMN created_at TEXT NOT NULL DEFAULT ''"
            )
        if "updated_at" not in columns:
            conn.execute(
                "ALTER TABLE tasks ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''"
            )
        conn.execute(
            "UPDATE tasks SET created_at = datetime('now'), updated_at = datetime('now')"
            " WHERE created_at = '' OR updated_at = ''"
        )
        # Search/filter hits the title column, so index it.
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_title ON tasks (title)")
        # Seeding runs inside this transaction, so it is all-or-nothing.
        count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO tasks (title, done) VALUES (?, ?)",
                SEED_TASKS,
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
    return {
        "id": row[0],
        "title": row[1],
        "done": bool(row[2]),
        "created_at": row[3],
        "updated_at": row[4],
    }


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
async def list_tasks(
    done: bool | None = None,
    search: str | None = None,
    sort: str | None = None,
):
    """List tasks, filtered and sorted by SQL: done status, title LIKE, ORDER BY title."""
    query = "SELECT * FROM tasks"
    conditions = []
    params = []
    if done is not None:
        conditions.append("done = ?")
        params.append(int(done))
    if search is not None:
        conditions.append("title LIKE ?")
        params.append(f"%{search}%")
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    if sort == "title":
        query += " ORDER BY title"
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [row_to_task(row) for row in rows]


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
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "INSERT INTO tasks (title, done, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (task_in.title, 0, now, now),
    )
    conn.commit()
    task_id = cur.lastrowid
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return row_to_task(row)


@app.put("/tasks/{task_id}")
async def update_task(task_id: int, task_in: TaskUpdate):
    """Replace a task's title and/or done flag. Unknown ids return 404."""
    if task_in.title is None and task_in.done is None:
        return JSONResponse(
            status_code=400,
            content={"error": "title or done is required"},
        )
    now = datetime.now(timezone.utc).isoformat()
    sets = ["updated_at = ?"]
    params = [now]
    if task_in.title is not None:
        sets.append("title = ?")
        params.append(task_in.title)
    if task_in.done is not None:
        sets.append("done = ?")
        params.append(int(task_in.done))
    params.append(task_id)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(f"UPDATE tasks SET {', '.join(sets)} WHERE id = ?", params)
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
    """Return counts computed by SQL, not by counting rows in code."""
    conn = sqlite3.connect(DB_PATH)
    total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    done = conn.execute("SELECT COUNT(*) FROM tasks WHERE done = 1").fetchone()[0]
    conn.close()
    return {"total": total, "done": done, "open": total - done}


@app.post("/reset")
async def reset():
    """Restore the original three example tasks."""
    conn = sqlite3.connect(DB_PATH)
    with conn:
        conn.execute("DELETE FROM tasks")
        conn.execute("DELETE FROM sqlite_sequence WHERE name = 'tasks'")
        conn.executemany(
            "INSERT INTO tasks (title, done) VALUES (?, ?)",
            SEED_TASKS,
        )
    conn.close()
    return {"status": "reset"}
