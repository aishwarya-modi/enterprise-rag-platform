from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from app.modules.eval.report import generate_html_report
from app.modules.eval.runner import get_run, list_runs, run_evaluation
from app.modules.eval.schemas import (
    EvaluationInput,
    EvaluationResult,
    ReportRequest,
    ReportResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/eval", tags=["Evaluation"])

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")


@router.post("/run", response_model=EvaluationResult)
async def evaluate(input_data: EvaluationInput) -> EvaluationResult:
    return await run_evaluation(input_data)


@router.get("/runs", response_model=list[EvaluationResult])
async def get_runs() -> list[EvaluationResult]:
    return list_runs()


@router.get("/runs/{run_id}", response_model=EvaluationResult)
async def get_evaluation_run(run_id: str) -> EvaluationResult:
    result = get_run(run_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return result


@router.post("/report", response_model=ReportResponse)
async def generate_report(request: ReportRequest) -> ReportResponse:
    result = get_run(request.run_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Run {request.run_id} not found")

    html_content = generate_html_report(result, title=request.title)
    filename = f"eval_report_{request.run_id[:8]}.html"

    os.makedirs(REPORTS_DIR, exist_ok=True)
    filepath = os.path.join(REPORTS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    return ReportResponse(run_id=request.run_id, html=html_content, filename=filename)


@router.get("/report/{run_id}", response_class=HTMLResponse)
async def get_report_html(run_id: str) -> HTMLResponse:
    result = get_run(run_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    html_content = generate_html_report(result)
    return HTMLResponse(content=html_content)
