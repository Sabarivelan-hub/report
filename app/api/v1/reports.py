"""API endpoints for Report Generation, Agent Workflow, Versioning, and Export."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.db.models import GeneratedReport, ReportVersion, GenerationLog
from app.schemas.report import (
    ReportCreateRequest,
    GeneratedReportOut,
    ReportVersionOut,
    GenerationLogOut,
)
from app.schemas.input_analysis import InputAnalysisOutput
from app.agents.input_analyzer import InputAnalysisAgent
from app.orchestrator.orchestrator import OrchestrationPipeline
from app.services.export_service import ExportService

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("/analyze-input", response_model=InputAnalysisOutput)
async def analyze_input_only(
    request: ReportCreateRequest,
):
    """
    Run Agent 1 (Input Analysis Agent) independently.
    Extracts structured factual entities and detects missing required fields
    without initiating the downstream generation pipeline.
    """
    agent = InputAnalysisAgent()
    structured = await agent.run(
        user_input=request.user_input,
        report_type_hint=request.report_type,
    )
    return structured


@router.post("/generate", response_model=GeneratedReportOut, status_code=status.HTTP_201_CREATED)
async def generate_report_pipeline(
    request: ReportCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Execute the full 5-stage Multi-Agent Workflow:
    1. Input Analysis Agent (factual extraction)
    2. Retrieval Agent (pgvector semantic search)
    3. Report Planner Agent (structure blueprint)
    4. Report Generator Agent (full synthesis)
    5. Validation Agent (integrity audit + retry loop if failed, max 2 attempts)
    """
    pipeline = OrchestrationPipeline(session=db)
    report = await pipeline.execute(request=request)

    # Reload with versions and logs
    stmt = (
        select(GeneratedReport)
        .where(GeneratedReport.id == report.id)
        .options(
            selectinload(GeneratedReport.versions),
            selectinload(GeneratedReport.logs)
        )
    )
    res = await db.execute(stmt)
    full_report = res.scalar_one()
    return full_report


@router.get("", response_model=List[GeneratedReportOut])
async def list_reports(
    report_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List recent reports with summary status."""
    stmt = select(GeneratedReport)
    if report_type:
        stmt = stmt.where(GeneratedReport.report_type == report_type)
    stmt = stmt.order_by(GeneratedReport.created_at.desc()).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/{report_id}", response_model=GeneratedReportOut)
async def get_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Fetch complete report data including final content, versions, and logs."""
    stmt = (
        select(GeneratedReport)
        .where(GeneratedReport.id == report_id)
        .options(
            selectinload(GeneratedReport.versions),
            selectinload(GeneratedReport.logs)
        )
    )
    res = await db.execute(stmt)
    report = res.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/{report_id}/versions", response_model=List[ReportVersionOut])
async def get_report_versions(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all iterative drafts generated during validation/regeneration cycles."""
    stmt = (
        select(ReportVersion)
        .where(ReportVersion.report_id == report_id)
        .order_by(ReportVersion.version_number.asc())
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/{report_id}/logs", response_model=List[GenerationLogOut])
async def get_report_logs(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Inspect granular agent execution audit logs, durations, and inputs/outputs."""
    stmt = (
        select(GenerationLog)
        .where(GenerationLog.report_id == report_id)
        .order_by(GenerationLog.created_at.asc())
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/{report_id}/export/{format}")
async def export_report(
    report_id: uuid.UUID,
    format: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Export the finalized report in PDF, DOCX, or JSON format.
    """
    stmt = select(GeneratedReport).where(GeneratedReport.id == report_id)
    res = await db.execute(stmt)
    report = res.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    content = report.final_content
    if not content:
        raise HTTPException(status_code=400, detail="Report has no generated content yet")

    filename_safe = f"report_{report.report_type}_{str(report.id)[:8]}"

    fmt = format.lower()
    if fmt == "json":
        json_str = ExportService.to_json(content)
        return Response(
            content=json_str,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename_safe}.json"'}
        )

    elif fmt == "docx":
        docx_buf = ExportService.to_docx(content)
        return StreamingResponse(
            docx_buf,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename_safe}.docx"'}
        )

    elif fmt == "pdf":
        pdf_buf = ExportService.to_pdf(content)
        return StreamingResponse(
            pdf_buf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename_safe}.pdf"'}
        )

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format '{format}'. Allowed: pdf, docx, json")
