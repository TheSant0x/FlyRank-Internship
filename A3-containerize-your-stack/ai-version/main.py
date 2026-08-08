"""AI-generated containerized Postgres task API (quarantined for review)."""

import os

import psycopg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

conn = psycopg.connect(os.environ["DATABASE_URL"])


def seed():
    with conn.cursor() as cur:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS tasks ("
            " id serial PRIMARY KEY, title text NOT NULL, done boolean DEFAULT false)"
        )
        count = cur.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        if count == 0:
            cur.executemany(
                "INSERT INTO tasks (title) VALUES (%s)",
                [("Buy milk",), ("Call the dentist",), ("Water the plants",)],
            )
        conn.commit()


seed()


class TaskIn(BaseModel):
    title: str


@app.get("/tasks")
def list_tasks():
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM tasks")
        rows = cur.fetchall()
    return [{"id": r[0], "title": r[1], "done": bool(r[2])} for r in rows]


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail={"error": "Task not found"})
    return {"id": row[0], "title": row[1], "done": bool(row[2])}


@app.post("/tasks", status_code=201)
def create_task(task_in: TaskIn):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO tasks (title) VALUES (%s) RETURNING *", (task_in.title,)
        )
        row = cur.fetchone()
        conn.commit()
    return {"id": row[0], "title": row[1], "done": bool(row[2])}


@app.put("/tasks/{task_id}")
def update_task(task_id: int, task_in: dict):
    title = task_in.get("title")
    done = task_in.get("done")
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE tasks SET title = COALESCE(%s, title), done = COALESCE(%s, done)"
            " WHERE id = %s RETURNING *",
            (title, done, task_id),
        )
        row = cur.fetchone()
        conn.commit()
    if row is None:
        raise HTTPException(status_code=404, detail={"error": "Task not found"})
    return {"id": row[0], "title": row[1], "done": bool(row[2])}


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail={"error": "Task not found"})
