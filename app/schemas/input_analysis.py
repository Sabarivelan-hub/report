"""Pydantic schemas for Agent 1 - Input Analysis Agent."""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class InputAnalysisOutput(BaseModel):
    """Structured extraction of user input conforming to strict factual constraints."""

    report_type: str = Field(
        ...,
        description="The identified type of report (e.g., 'industrial_visit', 'technical_audit', 'project_milestone')"
    )
    company: Optional[str] = Field(
        None,
        description="The host or client company/organization mentioned by user"
    )
    date: Optional[str] = Field(
        None,
        description="The date of the event/visit/audit in YYYY-MM-DD format if identifiable"
    )
    student_count: Optional[int] = Field(
        None,
        description="The number of attendees/students/participants"
    )
    department: Optional[str] = Field(
        None,
        description="The academic department, division, or organizational unit"
    )
    topics: List[str] = Field(
        default_factory=list,
        description="Key technical topics, agenda items, or technologies covered"
    )
    additional_information: List[str] = Field(
        default_factory=list,
        description="Any supplementary factual details explicitly stated in user input"
    )
    raw_entities: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extra extracted key-value parameters"
    )
    missing_required_fields: List[str] = Field(
        default_factory=list,
        description="Required fields for this report type that were not supplied in the input"
    )
