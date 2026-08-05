"""AI rematch attempt, regenerated after the first review, kept in quarantine."""

import sqlite3

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI()

conn = sqlite3.connect("tasks.db")
conn.execute(
    "CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, "
    "title TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0)"
)
if conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0:
    conn.executemany(
        "INSERT INTO tasks (title, done) VALUES (?, ?)",
        [("Buy milk", 0), ("Call the dentist", 0), ("Water the plants", 1)],
    )
conn.commit()


class TaskIn(BaseModel):
    title: str = Field(min_length=1)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    done: bool | None = None


def row_to_task(row):
    return {"id": row[0], "title": row[1], "done": bool(row[2])}


@app.get("/tasks")
def list_tasks():
    rows = conn.execute("SELECT id, title, done FROM tasks").fetchall()
    return [row_to_task(r) for r in rows]


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    row = conn.execute(
        "SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()
    if row is None:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    return row_to_task(row)


@app.post("/tasks", status_code=201)
def create_task(task_in: TaskIn):
    cur = conn.execute("INSERT INTO tasks (title) VALUES (?)", (task_in.title,))
    conn.commit()
    return {"id": cur.lastrowid, "title": task_in.title, "done": False}


@app.put("/tasks/{task_id}")
def update_task(task_id: int, task_in: TaskUpdate):
    if task_in.title is not None:
        conn.execute("UPDATE tasks SET title = ? WHERE id = ?", (task_in.title, task_id))
    if task_in.done is not None:
        conn.execute("UPDATE tasks SET done = ? WHERE id = ?", (int(task_in.done), task_id))
    conn.commit()
    row = conn.execute(
        "SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()
    if row is None:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    return row_to_task(row)


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    if cur.rowcount == 0:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    return None
