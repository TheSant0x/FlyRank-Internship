# PDF report generator

This Python/FastAPI service turns 200 seeded shop orders into a real multi-page sales report. It runs one SQL aggregation function, renders an HTML document with Playwright and headless Chromium, stores the PDF on disk, and returns a small link so the client downloads the artifact separately.

## Run it

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
python seed.py
uvicorn app.main:app --reload --port 8000
```

The API also exposes `GET /docs` for interactive Swagger documentation.

Generate a report:

```bash
curl -i -X POST http://127.0.0.1:8000/reports
```

Example response:

```json
{"id":"9e0f434c05c1","file":"/reports/9e0f434c05c1/file"}
```

The response is intentionally a link, not PDF bytes. Inspect it and download it with:

```bash
curl -o sales-report.pdf http://127.0.0.1:8000/reports/9e0f434c05c1/file
```

`GET /reports/9e0f434c05c1` returns the database row and the same link. An unknown id returns `404`.

## Dataset and SQL

The shop dataset has 200 invented orders with a customer, product, amount, and date. `python seed.py` deletes and recreates the rows, so running it repeatedly always leaves exactly 200 orders.

The report uses these aggregation queries from `app/report.py`:

```sql
SELECT COUNT(*) AS total_orders, COALESCE(SUM(amount), 0) AS total_revenue
FROM orders;

SELECT product, COUNT(*) AS order_count, ROUND(SUM(amount), 2) AS revenue
FROM orders GROUP BY product ORDER BY revenue DESC LIMIT 5;

SELECT created_at AS day, COUNT(*) AS order_count, ROUND(SUM(amount), 2) AS revenue
FROM orders WHERE created_at >= ? GROUP BY created_at ORDER BY created_at;
```

The first query supplies the two totals; the next two supply the top-five and date breakdown. The generated PDF also includes every order in a long detail table so the page-break behavior is visible. Its print CSS keeps rows together and repeats each table header using `thead { display: table-header-group; }`.

The first report is created with HTTP `201`. Asking again on the same day returns HTTP `200` with the same id and does not create another file. `{ "force": true }` deliberately creates a new report with `201`. This protects against double-clicks and browser retries; an equivalent missing check in a billing or email workflow could charge a customer or send the same invoice twice.

## Optional extras

- `POST /reports` accepts `{ "days": 7 }` to tune the date aggregation window.
- `GET /reports` lists generated reports and their links.
- Files receive descriptive names such as `sales-report-...pdf`.
- The PDF includes branded colors, a footer, repeated headings, totals, and an audit-friendly detail table.

The request-time pipeline is intentionally synchronous for this assignment. I would move query → render → save to a background job once reports become large, traffic becomes concurrent, or users stop accepting the visible wait; the user would get a fast status link, while the system would need durable pending/failed state.

## AI vs me

The generated comparison is in `ai-version/` and remains separate from the reviewed implementation. A sample `report.db`, generated PDFs, and the page-one screenshot are checked in under `reports/` for review.

### Generation prompt

> Build the same Python/FastAPI shop PDF report system. Use SQLite with an orders table containing id, customer, product, amount, and created_at, and a resettable seed script that creates exactly 200 rows. Implement one report-data function with COUNT/SUM totals, top five products by grouped revenue, and orders grouped by day for a configurable recent-days window. Build HTML from the data and render it with Python Playwright Chromium to an A4 PDF. Include print CSS that uses a table thead and break-inside: avoid for rows. Store PDFs in reports and add a reports table with id, path, and created_at. Implement POST /reports returning 201 with id and a file link, GET /reports/{id} returning the row or 404, and GET /reports/{id}/file serving the stored PDF or 404. A report already generated today must be returned with 200 and the same link; force=true must create a fresh 201 report. Include health, list reports, tests, pinned requirements, and safe path handling. Never put PDF bytes in JSON. Keep generated code in ai-version so it can be reviewed without replacing the hand-built version.

### Differences found

1. The hand-built version keeps SQL aggregation, rendering, and storage in separate modules (`app/report.py`, `app/pdf.py`, and `app/storage.py`); the comparison uses a more direct single-flow implementation.
2. The hand-built version serializes generation with a process lock and checks that an idempotent report file still exists before returning its link; the comparison relies on a simpler lookup path.
3. The hand-built tests check the exact 201/200/404 behavior, PDF bytes, repeated seed count, page count, and force behavior; the comparison has its own small smoke test but is not the submission source of truth.

The generated version was reviewed against the Stage 4 and Stage 5 checkpoints. A second pass tightened its file-path validation and made the once-per-day rule explicit. The hand-built version remains the implementation used by `app.main:app`.

## Verification and artifacts

- `python seed.py` twice leaves 200 orders.
- `python query_report.py` prints valid JSON with four report sections.
- `python generate_pdf.py` creates a six-page PDF from the seeded rows.
- `pdf-page-1.png` is a local screenshot of page 1 and is intentionally not committed.
- `pytest -q` covers the API and idempotency behavior.
