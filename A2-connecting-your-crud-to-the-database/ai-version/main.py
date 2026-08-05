"""AI-generated attempt, kept in quarantine for Stage 6 comparison."""

import sqlite3

from fastapi import FastAPI, HTTPException

app = FastAPI()

conn = sqlite3.connect("tasks.db")
conn.execute(
    "CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, "
    "title TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0)"
)


@app.get("/tasks")
def list_tasks():
    rows = conn.execute("SELECT id, title, done FROM tasks").fetchall()
    return [{"id": r[0], "title": r[1], "done": bool(r[2])} for r in rows]


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    row = conn.execute(
        "SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()
    return {"id": row[0], "title": row[1], "done": bool(row[2])}


@app.post("/tasks")
def create_task(title: str):
    cur = conn.execute("INSERT INTO tasks (title) VALUES (?)", (title,))
    conn.commit()
    return {"id": cur.lastrowid, "title": title, "done": False}


@app.put("/tasks/{task_id}")
def update_task(task_id: int, title: str = None, done: bool = None):
    if title is not None:
        conn.execute("UPDATE tasks SET title = ? WHERE id = ?", (title, task_id))
    if done is not None:
        conn.execute("UPDATE tasks SET done = ? WHERE id = ?", (int(done), task_id))
    conn.commit()
    row = conn.execute(
        "SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()
    return {"id": row[0], "title": row[1], "done": bool(row[2])}


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    return {"deleted": True}
