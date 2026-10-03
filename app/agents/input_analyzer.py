"""Agent 1 — Input Analysis Agent.

Converts unstructured user prompts into validated structured representations.
Strictly adheres to:
1. No report generation at this stage.
2. Extract only information factually supported by user input.
3. No hallucination or invention of missing values.
4. Identification of missing mandatory fields based on report type.
"""

import json
from typing import Optional, Dict, Any
from app.agents.base import BaseAgent
from app.schemas.input_analysis import InputAnalysisOutput

SYSTEM_INSTRUCTION = """You are the Input Analysis Agent in an AI Report Generation system.
Your sole responsibility is to analyze the user's raw input and convert it into a structured, factual JSON object.

CRITICAL RULES:
1. DO NOT generate the report or write report sections.
2. Extract ONLY factual information explicitly provided or directly implied by the user text.
3. DO NOT invent, extrapolate, or hallucinate missing dates, student numbers, company names, or topics. If a field is not stated, set it to null (or empty list for topics/additional_information).
4. Identify report_type: e.g. "industrial_visit", "technical_audit", "project_status", "internship", "seminar", or "general_report".
5. For the detected report_type, determine which standard required fields are missing:
   - For "industrial_visit": required are company, date, student_count, department, topics.
   - For other report types: identify relevant core missing parameters.
   List missing fields in 'missing_required_fields'.
6. Normalize dates to ISO-8601 (YYYY-MM-DD) if unambiguous.

Output must strictly be valid JSON matching this schema:
{
  "report_type": string,
  "company": string or null,
  "date": string (YYYY-MM-DD) or null,
  "student_count": integer or null,
  "department": string or null,
  "topics": [string],
  "additional_information": [string],
  "raw_entities": {},
  "missing_required_fields": [string]
}
"""


class InputAnalysisAgent(BaseAgent):
    """Agent responsible for factual extraction of user prompt into structured parameters."""

    def __init__(self, model_name: Optional[str] = None):
        super().__init__(agent_name="InputAnalysisAgent", model_name=model_name)

    async def run(self, user_input: str, report_type_hint: Optional[str] = None) -> InputAnalysisOutput:
        """Extract structured data from raw user narrative."""
        user_prompt = f"User Raw Request:\n\"\"\"\n{user_input}\n\"\"\"\n"
        if report_type_hint:
            user_prompt += f"\nNote: The user hinted that the report type is: {report_type_hint}."

        user_prompt += "\nExtract the structured parameters according to the defined schema. Remember: DO NOT INVENT DATA."

        raw_data = self._call_gemini_json(
            prompt=user_prompt,
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.1,  # Low temperature for deterministic extraction
        )

        # Validate with Pydantic
        structured = InputAnalysisOutput(**raw_data)
        return structured
