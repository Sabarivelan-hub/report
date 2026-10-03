"""Pydantic schemas for Report Planning, Generation, and Audit Logs."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field

from app.schemas.validation import ValidationResult


class ReportPlanSection(BaseModel):
    title: str = Field(..., description="Section title (e.g. 'Introduction', 'Objectives', 'Technical Sessions')")
    purpose: str = Field(..., description="The objective and expected content focus of this section")
    required: bool = Field(True, description="Whether this section is mandatory")
    reference_guidance: Optional[str] = Field(None, description="Key patterns/style adopted from retrieved references")


class ReportPlan(BaseModel):
    title: str = Field(..., description="Overall working title for the report")
    report_type: str = Field(..., description="Type of report")
    sections: List[ReportPlanSection] = Field(..., description="Ordered list of planned sections")
    rationale: Optional[str] = Field(None, description="Reasoning behind this structural plan")


class GeneratedSection(BaseModel):
    title: str
    content: str  # Markdown formatted text
    bullet_points: Optional[List[str]] = Field(default_factory=list)


class GeneratedReportContent(BaseModel):
    title: str
    subtitle: Optional[str] = None
    executive_summary: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    sections: List[GeneratedSection]
    conclusions_and_recommendations: Optional[str] = None


class ReportCreateRequest(BaseModel):
    user_input: str = Field(..., min_length=5, description="Raw user prompt or narrative describing the report requirements")
    template_id: Optional[UUID] = Field(None, description="Optional custom report template ID")
    report_type: Optional[str] = Field(None, description="Optional report type hint (e.g. industrial_visit)")
    user_id: Optional[UUID] = None


class ReportVersionOut(BaseModel):
    id: UUID
    report_id: UUID
    version_number: int
    content: Dict[str, Any]
    validation_result: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class GenerationLogOut(BaseModel):
    id: UUID
    report_id: UUID
    agent_name: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    execution_time: float
    status: str
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class GeneratedReportOut(BaseModel):
    id: UUID
    user_id: Optional[UUID]
    report_type: str
    input_data: Dict[str, Any]
    final_content: Optional[Dict[str, Any]]
    status: str
    created_at: datetime
    updated_at: datetime
    versions: Optional[List[ReportVersionOut]] = None
    logs: Optional[List[GenerationLogOut]] = None

    class Config:
        from_attributes = True
