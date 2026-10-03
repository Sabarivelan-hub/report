"""Multi-Agent Orchestrator coordinating the 5-step Report Generation Workflow.

Workflow:
USER INPUT
  ↓
1. INPUT ANALYSIS AGENT
  ↓
STRUCTURED INPUT
  ↓
2. RETRIEVAL AGENT (pgvector)
  ↓
RELEVANT REFERENCE DOCUMENTS
  ↓
3. REPORT PLANNER AGENT
  ↓
REPORT PLAN
  ↓
4. REPORT GENERATOR AGENT
  ↓
GENERATED DRAFT
  ↓
5. VALIDATION AGENT
  ↓
[If validation fails -> regenerate up to MAX_REGENERATION_ATTEMPTS (2)]
  ↓
FINAL REPORT + VERSIONS + AUDIT LOGS
"""

import uuid
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.config import settings
from app.db.models import GeneratedReport, ReportVersion, GenerationLog, ReportTemplate
from app.schemas.report import ReportCreateRequest, GeneratedReportContent, ReportPlan
from app.schemas.input_analysis import InputAnalysisOutput
from app.schemas.validation import ValidationResult
from app.agents.input_analyzer import InputAnalysisAgent
from app.agents.retrieval_agent import RetrievalAgent, RetrievalAgentResult
from app.agents.report_planner import ReportPlannerAgent
from app.agents.report_generator import ReportGeneratorAgent
from app.agents.validator import ValidationAgent

logger = logging.getLogger(__name__)


class OrchestrationPipeline:
    """Manages state, retry cycles, database persistence, and execution of the multi-agent graph."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.input_analyzer = InputAnalysisAgent()
        self.retrieval_agent = RetrievalAgent(session=session)
        self.report_planner = ReportPlannerAgent()
        self.report_generator = ReportGeneratorAgent()
        self.validator = ValidationAgent()

    async def log_step(
        self,
        report_id: uuid.UUID,
        agent_name: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        execution_time: float,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> GenerationLog:
        """Persist an audit log entry to the generation_logs table."""
        log_entry = GenerationLog(
            report_id=report_id,
            agent_name=agent_name,
            input_data=input_data,
            output_data=output_data,
            execution_time=execution_time,
            status=status,
            error_message=error_message,
        )
        self.session.add(log_entry)
        await self.session.commit()
        return log_entry

    async def execute(self, request: ReportCreateRequest) -> GeneratedReport:
        """Execute the end-to-end multi-agent report generation workflow."""
        # 1. Initialize GeneratedReport record
        report = GeneratedReport(
            user_id=request.user_id,
            report_type=request.report_type or "general_report",
            input_data={"raw_user_input": request.user_input, "template_id": str(request.template_id) if request.template_id else None},
            status="analyzing",
        )
        self.session.add(report)
        await self.session.commit()
        await self.session.refresh(report)

        report_id = report.id

        try:
            # ----------------------------------------------------
            # STEP 1: INPUT ANALYSIS AGENT
            # ----------------------------------------------------
            logger.info(f"[{report_id}] Executing Step 1: Input Analysis Agent")
            await self._update_report_status(report_id, "analyzing")

            structured_input, tel1 = await self.input_analyzer.execute_with_telemetry(
                user_input=request.user_input,
                report_type_hint=request.report_type
            )
            await self.log_step(
                report_id=report_id,
                agent_name="InputAnalysisAgent",
                input_data={"user_input": request.user_input},
                output_data=structured_input.model_dump(),
                execution_time=tel1["execution_time"],
                status=tel1["status"],
            )

            # Update report type if deduced
            if structured_input.report_type:
                report.report_type = structured_input.report_type
                report.input_data = {**report.input_data, "structured_input": structured_input.model_dump()}
                await self.session.commit()

            # ----------------------------------------------------
            # STEP 2: RETRIEVAL AGENT (pgvector)
            # ----------------------------------------------------
            logger.info(f"[{report_id}] Executing Step 2: Retrieval Agent")
            await self._update_report_status(report_id, "retrieving")

            retrieval_res, tel2 = await self.retrieval_agent.execute_with_telemetry(
                structured_input=structured_input,
                top_k=settings.DEFAULT_TOP_K,
            )
            await self.log_step(
                report_id=report_id,
                agent_name="RetrievalAgent",
                input_data=structured_input.model_dump(),
                output_data={
                    "search_query": retrieval_res.search_query,
                    "retrieved_chunk_count": len(retrieval_res.retrieved_chunks),
                    "chunks": [c.model_dump(mode="json") for c in retrieval_res.retrieved_chunks],
                },
                execution_time=tel2["execution_time"],
                status=tel2["status"],
            )

            # Check if template is requested from DB
            template_dict = None
            if request.template_id:
                tpl_stmt = select(ReportTemplate).where(ReportTemplate.id == request.template_id)
                tpl_res = await self.session.execute(tpl_stmt)
                tpl_obj = tpl_res.scalar_one_or_none()
                if tpl_obj:
                    template_dict = tpl_obj.template_structure

            # ----------------------------------------------------
            # STEP 3: REPORT PLANNER AGENT
            # ----------------------------------------------------
            logger.info(f"[{report_id}] Executing Step 3: Report Planner Agent")
            await self._update_report_status(report_id, "planning")

            report_plan, tel3 = await self.report_planner.execute_with_telemetry(
                structured_input=structured_input,
                retrieved_context=retrieval_res.summary_context,
                template=template_dict,
            )
            await self.log_step(
                report_id=report_id,
                agent_name="ReportPlannerAgent",
                input_data={"structured_input": structured_input.model_dump(), "has_template": bool(template_dict)},
                output_data=report_plan.model_dump(),
                execution_time=tel3["execution_time"],
                status=tel3["status"],
            )

            # ----------------------------------------------------
            # STEP 4 & 5: GENERATION & VALIDATION LOOP
            # Maximum regeneration attempts: 2 (total attempts up to 3)
            # ----------------------------------------------------
            max_attempts = settings.MAX_REGENERATION_ATTEMPTS + 1  # Initial attempt + up to 2 retries
            current_attempt = 1
            last_validation_feedback: Optional[ValidationResult] = None

            best_content: Optional[GeneratedReportContent] = None
            best_validation: Optional[ValidationResult] = None
            best_score = -1.0

            while current_attempt <= max_attempts:
                logger.info(f"[{report_id}] Generation Attempt {current_attempt}/{max_attempts}")
                await self._update_report_status(report_id, f"generating_v{current_attempt}")

                # 4. Generate report
                generated_content, tel4 = await self.report_generator.execute_with_telemetry(
                    structured_input=structured_input,
                    retrieved_context=retrieval_res.summary_context,
                    report_plan=report_plan,
                    template=template_dict,
                    validation_feedback=last_validation_feedback,
                )
                await self.log_step(
                    report_id=report_id,
                    agent_name=f"ReportGeneratorAgent_v{current_attempt}",
                    input_data={"attempt": current_attempt, "had_feedback": bool(last_validation_feedback)},
                    output_data={"title": generated_content.title, "section_count": len(generated_content.sections)},
                    execution_time=tel4["execution_time"],
                    status=tel4["status"],
                )

                # 5. Validate report
                await self._update_report_status(report_id, f"validating_v{current_attempt}")
                val_result, tel5 = await self.validator.execute_with_telemetry(
                    report_content=generated_content,
                    structured_input=structured_input,
                    report_plan=report_plan,
                )
                await self.log_step(
                    report_id=report_id,
                    agent_name=f"ValidationAgent_v{current_attempt}",
                    input_data={"attempt": current_attempt, "section_count": len(generated_content.sections)},
                    output_data=val_result.model_dump(),
                    execution_time=tel5["execution_time"],
                    status="success" if val_result.is_valid else "retry",
                )

                # Persist this version to report_versions table
                version_record = ReportVersion(
                    report_id=report_id,
                    version_number=current_attempt,
                    content=generated_content.model_dump(),
                    validation_result=val_result.model_dump(),
                )
                self.session.add(version_record)
                await self.session.commit()

                # Track best version
                if val_result.score > best_score:
                    best_score = val_result.score
                    best_content = generated_content
                    best_validation = val_result

                # Check termination conditions
                if val_result.is_valid:
                    logger.info(f"[{report_id}] Report passed validation on attempt {current_attempt} with score {val_result.score}")
                    break
                else:
                    logger.warning(
                        f"[{report_id}] Validation failed on attempt {current_attempt} (score: {val_result.score}). Issues: {len(val_result.issues)}"
                    )
                    last_validation_feedback = val_result
                    current_attempt += 1

            # ----------------------------------------------------
            # FINALIZE REPORT
            # ----------------------------------------------------
            final_content_dict = best_content.model_dump() if best_content else {}

            # If validation never completely passed after all attempts, attach warnings
            if best_validation and not best_validation.is_valid:
                final_content_dict["_validation_warnings"] = {
                    "passed": False,
                    "final_score": best_validation.score,
                    "attempts_made": min(current_attempt, max_attempts),
                    "warnings": best_validation.warnings,
                    "unresolved_issues": [i.model_dump() for i in best_validation.issues],
                    "recommendations": best_validation.recommendations,
                }
            elif best_validation:
                final_content_dict["_validation_summary"] = {
                    "passed": True,
                    "final_score": best_validation.score,
                    "attempts_made": min(current_attempt, max_attempts),
                    "warnings": best_validation.warnings,
                }

            report.final_content = final_content_dict
            report.status = "completed"
            await self.session.commit()
            await self.session.refresh(report)

            logger.info(f"[{report_id}] Pipeline completed successfully.")
            return report

        except Exception as e:
            logger.error(f"[{report_id}] Pipeline orchestration failed: {e}", exc_info=True)
            report.status = "failed"
            await self.session.commit()
            raise

    async def _update_report_status(self, report_id: uuid.UUID, status: str):
        """Update report status flag in database."""
        stmt = update(GeneratedReport).where(GeneratedReport.id == report_id).values(status=status)
        await self.session.execute(stmt)
        await self.session.commit()
