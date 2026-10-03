"""Agent 4 — Report Generator Agent.

Generates the complete, high-quality, professional report.
Rules:
1. Strictly follow the planned section structure.
2. User-provided information is the PRIMARY and absolute factual source.
3. Use retrieved references for structural style, tone, domain terminology, and technical phrasing.
4. DO NOT blindly copy reference reports; use them purely as contextual guidance.
5. In regeneration cycles, address validation feedback directly.
"""

from typing import Optional, Dict, Any, List
from app.agents.base import BaseAgent
from app.schemas.input_analysis import InputAnalysisOutput
from app.schemas.report import ReportPlan, GeneratedReportContent, GeneratedSection
from app.schemas.validation import ValidationResult

SYSTEM_INSTRUCTION = """You are the Report Generator Agent in an AI Report Generation system.
Your mission is to author a thorough, authoritative, and expertly articulated report adhering exactly to the approved Report Plan.

STRICT GENERATION DIRECTIVES:
1. PRIMARY FACTUAL SOURCE: The user-provided information (company, date, participants, topics, department) is the absolute factual bedrock. Never contradict or alter these facts.
2. CONTEXTUAL GUIDANCE: Incorporate domain knowledge, professional terminology, and explanatory frameworks from the retrieved reference documents. DO NOT blindly copy-paste reference paragraphs verbatim; synthesize them into fresh, tailored prose.
3. COMPLETENESS & DEPTH: Each section must be richly written with substantive technical paragraphs, bullet points, and specific observations rather than placeholder text or generic summaries.
4. SECTION FIDELITY: Generate every section defined in the Report Plan.
5. REGENERATION COMPLIANCE: If validation feedback or warnings from a prior iteration are provided, rigorously fix all flagged issues.

OUTPUT JSON FORMAT:
{
  "title": "Comprehensive Title of the Report",
  "subtitle": "Subtitle or Department Attribution",
  "executive_summary": "High-impact executive summary summarizing the background, key technical engagements, and primary findings.",
  "metadata": {
    "organization": "Company or Institution",
    "date": "YYYY-MM-DD",
    "department": "Department",
    "total_participants": "number"
  },
  "sections": [
    {
      "title": "Section Title",
      "content": "Rich markdown text with paragraphs, subheadings (###), and technical depth.",
      "bullet_points": ["Key takeaway 1", "Key takeaway 2"]
    }
  ],
  "conclusions_and_recommendations": "Forward-looking strategic recommendations and concluding takeaways."
}
"""


class ReportGeneratorAgent(BaseAgent):
    """Agent that writes the full text of the report based on plan and retrieved context."""

    def __init__(self, model_name: Optional[str] = None):
        super().__init__(agent_name="ReportGeneratorAgent", model_name=model_name)

    async def run(
        self,
        structured_input: InputAnalysisOutput,
        retrieved_context: str,
        report_plan: ReportPlan,
        template: Optional[Dict[str, Any]] = None,
        validation_feedback: Optional[ValidationResult] = None,
    ) -> GeneratedReportContent:
        """Generate the complete report content."""
        plan_summary = "\n".join(
            [f"- {s.title} (Required: {s.required}): {s.purpose} [Guidance: {s.reference_guidance or 'None'}]"
             for s in report_plan.sections]
        )

        prompt = (
            f"=== REPORT PLAN (SECTIONS TO GENERATE) ===\n"
            f"Title: {report_plan.title}\n"
            f"Type: {report_plan.report_type}\n"
            f"Sections:\n{plan_summary}\n\n"
            f"=== USER FACTUAL FOUNDATION ===\n"
            f"Company / Target: {structured_input.company or 'Unspecified'}\n"
            f"Date: {structured_input.date or 'Unspecified'}\n"
            f"Department: {structured_input.department or 'Unspecified'}\n"
            f"Student / Participant Count: {structured_input.student_count or 'Unspecified'}\n"
            f"Core Topics / Agenda: {', '.join(structured_input.topics) if structured_input.topics else 'General'}\n"
            f"Additional User Details: {'; '.join(structured_input.additional_information) if structured_input.additional_information else 'None'}\n\n"
            f"=== RETRIEVED REFERENCE GUIDANCE (STYLE, DOMAIN CONCEPTS & PATTERNS) ===\n"
            f"{retrieved_context}\n\n"
        )

        if template:
            prompt += f"=== TEMPLATE CONSTRAINTS ===\n{template}\n\n"

        if validation_feedback and not validation_feedback.is_valid:
            issues_str = "\n".join([f"- [{iss.severity.upper()}] ({iss.section or 'General'}): {iss.description}" for iss in validation_feedback.issues])
            recs_str = "\n".join([f"- {r}" for r in validation_feedback.recommendations])
            prompt += (
                f"=== CRITICAL REGENERATION FEEDBACK FROM VALIDATION AGENT ===\n"
                f"A previous draft failed validation. You MUST rectify these specific problems:\n"
                f"Issues to fix:\n{issues_str}\n"
                f"Recommendations:\n{recs_str}\n\n"
            )

        prompt += "Author the full, professional, highly articulated report adhering strictly to the plan and formatting guidelines."

        report_dict = self._call_gemini_json(
            prompt=prompt,
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.3,
        )

        return GeneratedReportContent(**report_dict)
