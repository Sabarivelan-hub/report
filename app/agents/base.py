"""Base Agent class providing execution telemetry, timing, and Gemini client initialization."""

import time
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)


class AgentExecutionError(Exception):
    """Raised when an AI agent encounters a fatal error during execution."""
    pass


class BaseAgent(ABC):
    """Abstract base class for all Gemini-based specialized agents."""

    def __init__(self, agent_name: str, model_name: Optional[str] = None):
        self.agent_name = agent_name
        self.model_name = model_name or settings.GEMINI_GENERATION_MODEL
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    @abstractmethod
    async def run(self, *args, **kwargs) -> Any:
        """Execute the agent's core capability."""
        pass

    async def execute_with_telemetry(self, *args, **kwargs) -> Tuple[Any, Dict[str, Any]]:
        """Run agent and record execution telemetry for generation_logs."""
        start_time = time.perf_counter()
        status = "success"
        error_message = None
        output = None

        try:
            output = await self.run(*args, **kwargs)
            return output, {
                "agent_name": self.agent_name,
                "execution_time": round(time.perf_counter() - start_time, 4),
                "status": status,
                "error_message": None,
            }
        except Exception as e:
            status = "failure"
            error_message = str(e)
            logger.error(f"Agent {self.agent_name} failed: {e}", exc_info=True)
            raise AgentExecutionError(f"{self.agent_name} execution error: {e}") from e

    def _call_gemini_json(
        self,
        prompt: str,
        system_instruction: str,
        response_schema: Any = None,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """Helper to invoke Gemini with JSON mode / structured schema output."""
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
                response_mime_type="application/json",
            )
            if response_schema is not None:
                config.response_schema = response_schema

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )

            text_output = response.text
            if not text_output:
                raise ValueError("Empty response received from Gemini model.")

            # Parse JSON
            data = json.loads(text_output)
            return data

        except json.JSONDecodeError as jde:
            logger.error(f"Gemini returned invalid JSON: {jde}. Raw text: {text_output}")
            # Clean markdown codeblocks if model inadvertently added ```json ... ```
            cleaned = text_output.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            return json.loads(cleaned.strip())
        except Exception as e:
            logger.error(f"Gemini API call failed in {self.agent_name}: {e}")
            raise
