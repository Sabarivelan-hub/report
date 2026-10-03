"""Pydantic schemas for Report Templates."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class TemplateSection(BaseModel):
    title: str
    purpose: str
    required: bool = True
    guidelines: Optional[str] = None


class TemplateStructure(BaseModel):
    sections: List[TemplateSection]
    tone: Optional[str] = "Professional and technical"
    expected_length: Optional[str] = "Comprehensive"


class ReportTemplateBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    report_type: str = Field(..., max_length=100)
    template_structure: TemplateStructure


class ReportTemplateCreate(ReportTemplateBase):
    pass


class ReportTemplateOut(ReportTemplateBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
