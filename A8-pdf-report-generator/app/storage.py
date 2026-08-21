from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

DB_PATH = Path(os.getenv("DATABASE_PATH", "report.db"))
REPORTS_DIR = Path(os.getenv("REPORTS_DIR", "reports"))
TIMEZONE = ZoneInfo(os.getenv("REPORT_TIMEZONE", "Africa/Cairo"))


def now() -> datetime:
    return datetime.now(TIMEZONE)


def initialize_reports_table() -> None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)


def insert_report(report_id: str, path: str, created_at: str) -> None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("INSERT INTO reports(id, path, created_at) VALUES (?, ?, ?)", (report_id, path, created_at))


def find_report(report_id: str) -> dict | None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute("SELECT id, path, created_at FROM reports WHERE id = ?", (report_id,)).fetchone()
    return dict(row) if row else None


def find_report_created_today() -> dict | None:
    today = now().date().isoformat()
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute("SELECT id, path, created_at FROM reports WHERE created_at LIKE ? ORDER BY created_at DESC LIMIT 1", (f"{today}%",)).fetchone()
    return dict(row) if row else None


def report_file_exists(report: dict) -> bool:
    return Path(report["path"]).is_file()


def list_reports() -> list[dict]:
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute("SELECT id, path, created_at FROM reports ORDER BY created_at DESC")]
