"""Agent 5 — Validation Agent.

Audits generated reports for:
1. Presence of all mandatory planned sections
2. Strict factual consistency against user-provided inputs
3. Absence of unauthorized hallucinations or contradictory dates/numbers
4. Technical depth and completeness
5. Professional tone and formatting
"""

from typing import Optional, Dict, Any, List
from app.agents.base import BaseAgent
from app.schemas.input_analysis import InputAnalysisOutput
from app.schemas.report import ReportPlan, GeneratedReportContent
from app.schemas.validation import ValidationResult, ValidationChecklist, ValidationErrorItem

SYSTEM_INSTRUCTION = """You are the Senior Validation Agent in an automated Report Generation system.
Your mission is to perform an uncompromising quality and factual integrity audit on the generated report.

VALIDATION CHECKLIST:
1. required_sections_present: Ensure every section marked 'required: true' in the Report Plan is present in the generated report with substantive content.
2. factual_consistency: Verify that user facts (company name, dates, participant counts, department, specified topics) are accurately represented without corruption.
3. no_hallucinated_facts: Verify that the generator has NOT fabricated contradictory numerical statistics, false client names, or unsupported definitive facts outside the reference domain context.
4. completeness: Verify that each section contains sufficient technical depth, coherent explanations, and appropriate length (not empty or trivial 1-liners).
5. tone_and_formatting: Check for professional, structured markdown formatting, executive tone, and absence of AI meta-commentary (e.g. 'As an AI...').

SCORING & VERDICT:
- score: float from 0.0 to 1.0
- is_valid: true IF AND ONLY IF all critical checks pass and score >= 0.80.
- If any required section is completely missing, is_valid MUST BE false.
- If user facts are contradicted, is_valid MUST BE false.
- Categorize each issue: "missing_section", "factual_discrepancy", "hallucination", "shallow_content", "formatting".
- Severity: "critical" (triggers regeneration) or "warning".
- Provide clear, actionable recommendations for remediation.

OUTPUT JSON FORMAT:
{
  "is_valid": true/false,
  "score": 0.92,
  "checks": {
    "required_sections_present": true/false,
    "factual_consistency": true/false,
    "no_hallucinated_facts": true/false,
    "completeness": true/false,
    "tone_and_formatting": true/false
  },
  "issues": [
    {
      "category": "factual_discrepancy",
      "severity": "critical",
      "section": "Technical Sessions",
      "description": "Student count was mentioned as 50 instead of 52."
    }
  ],
  "warnings": ["Section 3 could include more specific architectural diagrams."],
  "recommendations": ["Re-align participant count to exactly 52.", "Add depth to cloud session."]
}
"""


class ValidationAgent(BaseAgent):
    """Agent that performs multi-criteria automated QA and factual audit on reports."""

    def __init__(self, model_name: Optional[str] = None):
        super().__init__(agent_name="ValidationAgent", model_name=model_name)

    async def run(
        self,
        report_content: GeneratedReportContent,
        structured_input: InputAnalysisOutput,
        report_plan: ReportPlan,
    ) -> ValidationResult:
        """Perform validation audit against plan and ground-truth user inputs."""
        all_section_titles = [s.title for s in report_content.sections]
        if report_content.executive_summary:
            all_section_titles.append("Executive Summary")
        if report_content.conclusions_and_recommendations:
            all_section_titles.extend(["Conclusion", "Conclusion & Recommendations", "Conclusion and Strategic Recommendations", "Conclusions and Recommendations"])

        generated_summary = {
            "title": report_content.title,
            "executive_summary_preview": report_content.executive_summary[:200] + "...",
            "sections_present": all_section_titles,
            "total_sections": len(report_content.sections),
            "metadata": report_content.metadata,
            "full_sections": [{"title": s.title, "char_count": len(s.content), "text": s.content} for s in report_content.sections],
            "conclusions_and_recommendations": report_content.conclusions_and_recommendations,
        }

        required_sections = [s.title for s in report_plan.sections if s.required]

        prompt = (
            f"=== GROUND TRUTH USER FACTS ===\n"
            f"Company: {structured_input.company}\n"
            f"Date: {structured_input.date}\n"
            f"Student/Participant Count: {structured_input.student_count}\n"
            f"Department: {structured_input.department}\n"
            f"Mandatory Topics: {structured_input.topics}\n"
            f"Additional Info: {structured_input.additional_information}\n\n"
            f"=== REQUIRED SECTIONS IN PLAN ===\n"
            f"{required_sections}\n\n"
            f"=== GENERATED REPORT CONTENT TO AUDIT ===\n"
            f"{generated_summary}\n\n"
            f"Perform the complete verification audit and output structured JSON."
        )

        validation_dict = self._call_gemini_json(
            prompt=prompt,
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.1,  # Deterministic evaluation
        )

        return ValidationResult(**validation_dict)
