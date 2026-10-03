"""Pydantic schemas for Agent 5 - Validation Agent."""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class ValidationChecklist(BaseModel):
    required_sections_present: bool = Field(..., description="All mandatory sections from plan/template are included")
    factual_consistency: bool = Field(..., description="Facts match user input (dates, numbers, companies, topics)")
    no_hallucinated_facts: bool = Field(..., description="No fabricated statistics, attendees, or dates outside source")
    completeness: bool = Field(..., description="Sufficient depth and technical content in each section")
    tone_and_formatting: bool = Field(..., description="Adheres to professional formatting and objective tone")


class ValidationErrorItem(BaseModel):
    category: str  # missing_section, factual_discrepancy, hallucination, shallow_content, formatting
    severity: str  # critical, warning, suggestion
    section: Optional[str] = None
    description: str


class ValidationResult(BaseModel):
    is_valid: bool = Field(..., description="True if report passes all critical checks")
    score: float = Field(..., ge=0.0, le=1.0, description="Quality score from 0.0 to 1.0")
    checks: ValidationChecklist
    issues: List[ValidationErrorItem] = Field(default_factory=list, description="Critical issues triggering regeneration")
    warnings: List[str] = Field(default_factory=list, description="Non-blocking observations")
    recommendations: List[str] = Field(default_factory=list, description="Actionable improvement suggestions for regeneration")
