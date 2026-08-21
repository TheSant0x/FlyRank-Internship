import os
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

DB_PATH = Path(os.getenv("DATABASE_PATH", "report.db"))
PRODUCTS = ("Atlas mug", "Field notebook", "Desk lamp", "Canvas tote", "Travel bottle", "Cable organizer")


def seed() -> int:
    rng = random.Random(804)
    today = date.today()
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("DROP TABLE IF EXISTS orders")
        connection.execute("""
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                customer TEXT NOT NULL,
                product TEXT NOT NULL,
                amount REAL NOT NULL CHECK (amount >= 5 AND amount <= 200),
                created_at TEXT NOT NULL
            )
        """)
        rows = [
            (
                f"Customer {index:03d}",
                rng.choice(PRODUCTS),
                round(rng.uniform(5, 200), 2),
                (today - timedelta(days=rng.randrange(30))).isoformat(),
            )
            for index in range(1, 201)
        ]
        connection.executemany("INSERT INTO orders(customer, product, amount, created_at) VALUES (?, ?, ?, ?)", rows)
    return len(rows)

if __name__ == "__main__":
    print(f"Seeded {seed()} orders into {DB_PATH}")
