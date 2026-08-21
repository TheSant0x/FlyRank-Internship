from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any

SUMMARY_SQL = """
SELECT COUNT(*) AS total_orders, COALESCE(SUM(amount), 0) AS total_revenue
FROM orders
"""
TOP_PRODUCTS_SQL = """
SELECT product, COUNT(*) AS order_count, ROUND(SUM(amount), 2) AS revenue
FROM orders GROUP BY product ORDER BY revenue DESC LIMIT 5
"""
ORDERS_BY_DAY_SQL = """
SELECT created_at AS day, COUNT(*) AS order_count, ROUND(SUM(amount), 2) AS revenue
FROM orders WHERE created_at >= ? GROUP BY created_at ORDER BY created_at
"""


def get_report_data(db_path: str | Path = "report.db", days: int = 7) -> dict[str, Any]:
    if days < 1 or days > 30:
        raise ValueError("days must be between 1 and 30")
    since = (date.today() - timedelta(days=days - 1)).isoformat()
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        summary = dict(connection.execute(SUMMARY_SQL).fetchone())
        top_products = [dict(row) for row in connection.execute(TOP_PRODUCTS_SQL)]
        orders_by_day = [dict(row) for row in connection.execute(ORDERS_BY_DAY_SQL, (since,))]
    summary["total_revenue"] = round(float(summary["total_revenue"]), 2)
    return {
        "summary": summary,
        "top_products": top_products,
        "orders_by_day": orders_by_day,
        "period": {"days": days, "from": since, "to": date.today().isoformat()},
    }
