from __future__ import annotations

import html
import sqlite3
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright

from .report import get_report_data


def _money(value: float) -> str:
    return f"${value:,.2f}"


def build_html(report: dict, orders: list[dict]) -> str:
    summary = report["summary"]
    products = "".join(
        f"<tr><td>{html.escape(row['product'])}</td><td>{row['order_count']}</td><td>{_money(row['revenue'])}</td></tr>"
        for row in report["top_products"]
    )
    order_rows = "".join(
        f"<tr><td>#{row['id']:03d}</td><td>{html.escape(row['customer'])}</td><td>{html.escape(row['product'])}</td><td>{_money(row['amount'])}</td><td>{row['created_at']}</td></tr>"
        for row in orders
    )
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
@page {{ size: A4; margin: 18mm 15mm 16mm; }}
* {{ box-sizing: border-box; }}
body {{ font-family: Arial, sans-serif; color: #17202b; margin: 0; font-size: 10px; }}
.header {{ display: flex; justify-content: space-between; align-items: end; border-bottom: 3px solid #176b5b; padding-bottom: 13px; margin-bottom: 20px; }}
h1 {{ margin: 0; font-size: 25px; letter-spacing: -0.8px; }}
.kicker {{ color: #176b5b; font-size: 9px; font-weight: bold; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 5px; }}
.date {{ color: #697586; font-size: 10px; }}
.summary {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 22px; }}
.metric {{ background: #f0f7f4; border: 1px solid #d6eae3; border-radius: 5px; padding: 13px; }}
.metric-label {{ color: #5b746d; font-size: 9px; text-transform: uppercase; letter-spacing: .8px; }}
.metric-value {{ font-size: 21px; font-weight: bold; margin-top: 5px; color: #124e43; }}
h2 {{ font-size: 13px; margin: 18px 0 8px; }}
table {{ width: 100%; border-collapse: collapse; margin-bottom: 18px; }}
thead {{ display: table-header-group; }}
th {{ background: #17202b; color: white; text-align: left; font-size: 9px; padding: 7px 6px; }}
td {{ border-bottom: 1px solid #e3e7eb; padding: 6px; font-size: 9px; }}
tr {{ break-inside: avoid; page-break-inside: avoid; }}
.small {{ color: #697586; font-size: 9px; }}
.footer {{ color: #8793a0; font-size: 8px; border-top: 1px solid #dfe4ea; padding-top: 7px; margin-top: 12px; }}
</style></head><body>
<div class="header"><div><div class="kicker">Branchline reports</div><h1>Sales performance</h1></div><div class="date">Generated {date.today().isoformat()}<br>Last {report['period']['days']} days</div></div>
<div class="summary"><div class="metric"><div class="metric-label">Total orders</div><div class="metric-value">{summary['total_orders']}</div></div><div class="metric"><div class="metric-label">Total revenue</div><div class="metric-value">{_money(summary['total_revenue'])}</div></div></div>
<h2>Top products by revenue</h2><table><thead><tr><th>Product</th><th>Orders</th><th>Revenue</th></tr></thead><tbody>{products}</tbody></table>
<h2>Orders by day</h2><table><thead><tr><th>Date</th><th>Orders</th><th>Revenue</th></tr></thead><tbody>{''.join(f"<tr><td>{row['day']}</td><td>{row['order_count']}</td><td>{_money(row['revenue'])}</td></tr>" for row in report['orders_by_day'])}</tbody></table>
<h2>Order detail</h2><p class="small">All {len(orders)} seeded orders, included for auditability.</p><table><thead><tr><th>ID</th><th>Customer</th><th>Product</th><th>Amount</th><th>Date</th></tr></thead><tbody>{order_rows}</tbody></table>
<div class="footer">Generated from the local SQLite order ledger · Confidential development report</div>
</body></html>"""


def render_report(db_path: str | Path, output_path: str | Path, days: int = 7) -> Path:
    report = get_report_data(db_path, days=days)
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        orders = [dict(row) for row in connection.execute("SELECT id, customer, product, amount, created_at FROM orders ORDER BY created_at DESC, id DESC")]
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    markup = build_html(report, orders)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_content(markup, wait_until="load")
        page.pdf(path=str(destination), format="A4", print_background=True)
        browser.close()
    return destination
