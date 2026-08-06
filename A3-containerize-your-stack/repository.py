"""The only module that talks to Postgres. Routes never touch SQL directly."""

import os

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()

SEED_TASKS = [
    ("Buy milk", False),
    ("Call the dentist", False),
    ("Water the plants", True),
]


def get_conn():
    """Open a connection using the DATABASE_URL secret from .env."""
    return psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row)


def init_db():
    """Create the tasks table if missing, and seed three tasks only when empty."""
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id serial PRIMARY KEY,
                title text NOT NULL,
                done boolean NOT NULL DEFAULT false
            )
            """
        )
        count = conn.execute("SELECT COUNT(*) AS n FROM tasks").fetchone()["n"]
        if count == 0:
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO tasks (title, done) VALUES (%s, %s)",
                    SEED_TASKS,
                )


def row_to_task(row):
    """Convert a Postgres row to the JSON shape the API has always returned."""
    return {
        "id": row["id"],
        "title": row["title"],
        "done": bool(row["done"]),
    }


def list_tasks(done=None, search=None, sort=None):
    """List tasks, filtered and sorted by SQL: done status, title LIKE, ORDER BY title."""
    query = "SELECT * FROM tasks"
    conditions = []
    params = []
    if done is not None:
        conditions.append("done = %s")
        params.append(done)
    if search is not None:
        conditions.append("title ILIKE %s")
        params.append(f"%{search}%")
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    if sort == "title":
        query += " ORDER BY title"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [row_to_task(row) for row in rows]


def get_task(task_id):
    """Return one task by id, or None when it does not exist."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = %s", (task_id,)
        ).fetchone()
    return row_to_task(row) if row else None
