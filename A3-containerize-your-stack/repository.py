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
