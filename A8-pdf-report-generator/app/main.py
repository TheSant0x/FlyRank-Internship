from __future__ import annotations

import uuid
from pathlib import Path
from threading import Lock

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

load_dotenv()

from .pdf import render_report
from .storage import DB_PATH, REPORTS_DIR, find_report, find_report_created_today, initialize_reports_table, insert_report, list_reports, now, report_file_exists

app = FastAPI(title="FlyRank PDF Report Generator", version="1.0.0")
_generation_lock = Lock()

class ReportRequest(BaseModel):
    days: int = Field(default=7, ge=1, le=30)
    force: bool = False

@app.on_event("startup")
def startup() -> None:
    initialize_reports_table()

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.post("/reports", status_code=201)
def create_report(request: ReportRequest | None = None) -> dict[str, str]:
    options = request or ReportRequest()
    if not options.force:
        existing = find_report_created_today()
        if existing and report_file_exists(existing):
            return JSONResponse(status_code=200, content={"id": existing["id"], "file": f"/reports/{existing['id']}/file"})
    report_id = uuid.uuid4().hex[:12]
    destination = REPORTS_DIR / f"sales-report-{now().date().isoformat()}-{report_id}.pdf"
    try:
        with _generation_lock:
            render_report(DB_PATH, destination, days=options.days)
            insert_report(report_id, str(destination), now().isoformat())
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Could not generate report: {error}") from error
    return {"id": report_id, "file": f"/reports/{report_id}/file"}

@app.get("/reports/{report_id}")
def get_report(report_id: str) -> dict:
    report = find_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {**report, "file": f"/reports/{report_id}/file"}

@app.get("/reports/{report_id}/file")
def download_report(report_id: str):
    report = find_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    path = report["path"]
    if not Path(path).is_file():
        raise HTTPException(status_code=404, detail="Report file not found")
    return FileResponse(path, media_type="application/pdf", filename=Path(path).name)
