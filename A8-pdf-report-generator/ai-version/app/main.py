from __future__ import annotations

import uuid
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from .pdf import render_report
from .storage import (
    DB_PATH,
    REPORTS_DIR,
    find_report,
    find_report_created_today,
    initialize_reports_table,
    insert_report,
    list_reports,
    now,
    report_file_exists,
)

app = FastAPI(title="FlyRank PDF Report Generator (AI version)", version="1.0.0")
lock = Lock()

class ReportRequest(BaseModel):
    days: int = Field(default=7, ge=1, le=30)
    force: bool = False

@app.on_event("startup")
def setup() -> None:
    initialize_reports_table()

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.post("/reports", status_code=201)
def create_report(request: ReportRequest | None = None):
    options = request or ReportRequest()
    if not options.force:
        existing = find_report_created_today()
        if existing and report_file_exists(existing):
            return JSONResponse(status_code=200, content={"id": existing["id"], "file": f"/reports/{existing['id']}/file"})
    report_id = uuid.uuid4().hex[:12]
    path = REPORTS_DIR / f"sales-report-{now().date().isoformat()}-{report_id}.pdf"
    try:
        with lock:
            render_report(DB_PATH, path, options.days)
            insert_report(report_id, str(path), now().isoformat())
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Could not generate report: {error}") from error
    return {"id": report_id, "file": f"/reports/{report_id}/file"}

@app.get("/reports")
def reports() -> list[dict]:
    return [{**row, "file": f"/reports/{row['id']}/file"} for row in list_reports()]

@app.get("/reports/{report_id}")
def report(report_id: str) -> dict:
    row = find_report(report_id)
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    return {**row, "file": f"/reports/{report_id}/file"}

@app.get("/reports/{report_id}/file")
def report_file(report_id: str):
    row = find_report(report_id)
    if not row or not Path(row["path"]).is_file():
        raise HTTPException(status_code=404, detail="Report file not found")
    return FileResponse(row["path"], media_type="application/pdf", filename=Path(row["path"]).name)
