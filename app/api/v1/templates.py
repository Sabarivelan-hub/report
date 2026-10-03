"""API endpoints for Report Templates."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db
from app.db.models import ReportTemplate
from app.schemas.template import ReportTemplateCreate, ReportTemplateOut

router = APIRouter(prefix="/templates", tags=["Report Templates"])


@router.post("", response_model=ReportTemplateOut, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_in: ReportTemplateCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new standardized report template structure."""
    db_obj = ReportTemplate(
        name=template_in.name,
        description=template_in.description,
        report_type=template_in.report_type,
        template_structure=template_in.template_structure.model_dump(),
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


@router.get("", response_model=List[ReportTemplateOut])
async def list_templates(
    report_type: Optional[str] = Query(None, description="Filter by report type"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve available report templates."""
    stmt = select(ReportTemplate)
    if report_type:
        stmt = stmt.where(ReportTemplate.report_type == report_type)
    stmt = stmt.order_by(ReportTemplate.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{template_id}", response_model=ReportTemplateOut)
async def get_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Fetch details of a specific report template."""
    stmt = select(ReportTemplate).where(ReportTemplate.id == template_id)
    result = await db.execute(stmt)
    tpl = result.scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=404, detail="Report template not found")
    return tpl
