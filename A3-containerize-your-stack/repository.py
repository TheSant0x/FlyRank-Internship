"""The only module that talks to Postgres. Routes never touch SQL directly."""

import os

import psycopg
import redis
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


def ping_db():
    """Run SELECT 1 so /health can report the database is reachable."""
    with get_conn() as conn:
        conn.execute("SELECT 1")


def ping_redis():
    """PING the Redis service; real companies gate deploys on this."""
    r = redis.Redis(host="redis", port=6379, socket_timeout=2)
    r.ping()


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


def create_task(title):
    """Insert a task with done=false and hand back the new row, id included."""
    with get_conn() as conn:
        row = conn.execute(
            "INSERT INTO tasks (title, done) VALUES (%s, false) RETURNING *",
            (title,),
        ).fetchone()
    return row_to_task(row)


def update_task(task_id, title=None, done=None):
    """Update a task's title and/or done flag. Returns None when id is unknown."""
    sets = []
    params = []
    if title is not None:
        sets.append("title = %s")
        params.append(title)
    if done is not None:
        sets.append("done = %s")
        params.append(done)
    if not sets:
        return None
    params.append(task_id)
    with get_conn() as conn:
        row = conn.execute(
            f"UPDATE tasks SET {', '.join(sets)} WHERE id = %s RETURNING *",
            params,
        ).fetchone()
    return row_to_task(row) if row else None


def delete_task(task_id):
    """Delete a task. Returns True when a row was removed, False for unknown ids."""
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
        return cur.rowcount > 0


def stats():
    """Return counts computed by SQL, not by counting rows in code."""
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) AS n FROM tasks").fetchone()["n"]
        done = conn.execute(
            "SELECT COUNT(*) AS n FROM tasks WHERE done = true"
        ).fetchone()["n"]
    return {"total": total, "done": done, "open": total - done}


def reset():
    """Restore the original three example tasks."""
    with get_conn() as conn:
        conn.execute("DELETE FROM tasks")
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO tasks (title, done) VALUES (%s, %s)",
                SEED_TASKS,
            )
