"""Agent 3 — Report Planner Agent.

Determines the comprehensive structure, section breakdown, and purpose
of each report section before generation.
Follows configured report templates when provided, enriched by retrieved reference patterns.
"""

from typing import Optional, Dict, Any, List
from app.agents.base import BaseAgent
from app.schemas.input_analysis import InputAnalysisOutput
from app.schemas.report import ReportPlan, ReportPlanSection
from app.schemas.template import ReportTemplateOut, TemplateStructure

SYSTEM_INSTRUCTION = """You are the Report Planner Agent in an AI Report Generation system.
Your goal is to define a clean, logically organized, and professional section-by-section plan for the final report.

MANDATORY RULES:
1. If a configured report template is provided, you MUST strictly follow its prescribed section structure and required sections. You may elaborate on section purposes based on the reference patterns and user specifics, but do NOT remove template-mandated sections.
2. If no template is provided, deduce the most effective standard structure from the retrieved reference documents and the report type (e.g. for industrial visits: Introduction, Company Profile, Objectives of the Visit, Technical Sessions & Architecture, Student Engagement & Key Observations, Learning Outcomes, Conclusion & Recommendations).
3. Every section must have:
   - title: concise heading
   - purpose: specific goal and topics to address
   - required: boolean (true for essential sections)
   - reference_guidance: styling or structural cues from the references
4. Do NOT generate the report body text here. Only generate the structural blueprint.

Output JSON format:
{
  "title": "Working Title of the Report",
  "report_type": "type of report",
  "rationale": "Brief justification for this structural breakdown",
  "sections": [
    {
      "title": "Introduction",
      "purpose": "State the event context, date, attendees, and academic background",
      "required": true,
      "reference_guidance": "Follow standard academic header format"
    }
  ]
}
"""


class ReportPlannerAgent(BaseAgent):
    """Agent that devises the structural outline and requirements of the report."""

    def __init__(self, model_name: Optional[str] = None):
        super().__init__(agent_name="ReportPlannerAgent", model_name=model_name)

    async def run(
        self,
        structured_input: InputAnalysisOutput,
        retrieved_context: str,
        template: Optional[Dict[str, Any]] = None,
    ) -> ReportPlan:
        """Create a tailored report outline based on user specs, references, and optional template."""
        prompt = (
            f"=== STRUCTURED USER INPUT ===\n"
            f"Report Type: {structured_input.report_type}\n"
            f"Company: {structured_input.company or 'N/A'}\n"
            f"Date: {structured_input.date or 'N/A'}\n"
            f"Student Count: {structured_input.student_count or 'N/A'}\n"
            f"Department: {structured_input.department or 'N/A'}\n"
            f"Topics: {', '.join(structured_input.topics) if structured_input.topics else 'General'}\n"
            f"Additional Info: {'; '.join(structured_input.additional_information) if structured_input.additional_information else 'None'}\n\n"
        )

        if template:
            prompt += f"=== CONFIGURED REPORT TEMPLATE (MANDATORY TO FOLLOW) ===\n{template}\n\n"
        else:
            prompt += "=== CONFIGURED REPORT TEMPLATE ===\nNo custom template assigned; use standard industry structure informed by references.\n\n"

        prompt += (
            f"=== RETRIEVED REFERENCE CHUNKS ===\n"
            f"{retrieved_context}\n\n"
            f"Devise the complete, structured section plan for this report in JSON."
        )

        plan_dict = self._call_gemini_json(
            prompt=prompt,
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.2,
        )

        # Validate with Pydantic
        return ReportPlan(**plan_dict)
