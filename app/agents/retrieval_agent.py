"""Agent 2 — Retrieval Agent.

Orchestrates semantic retrieval by transforming structured user input into optimized
vector queries and retrieving the top-K relevant reference document chunks via
the independent pgvector repository layer.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.schemas.input_analysis import InputAnalysisOutput
from app.rag.embeddings import EmbeddingService, embedding_service
from app.rag.retriever import VectorRetrieverRepository, RetrievedReference

SYSTEM_INSTRUCTION = """You are the Retrieval Agent in a RAG-based Report Generation platform.
Your task is to take structured input parameters and synthesize an optimal semantic query to find the most relevant reference report chunks.
The query should capture:
1. The domain, industry, and topic keywords
2. Structural report requirements (e.g. objectives, technical sessions, outcomes, methodology)
3. Tone and expected technical depth

Output valid JSON:
{
  "search_query": "concise semantic query string for embedding generation",
  "focus_areas": ["list of key conceptual topics to guide filtering"]
}
"""


class RetrievalAgentResult(BaseModel):
    search_query: str
    focus_areas: List[str]
    retrieved_chunks: List[RetrievedReference]
    summary_context: str


class RetrievalAgent(BaseAgent):
    """Agent that handles intelligent semantic query formulation and invokes vector retrieval."""

    def __init__(
        self,
        session: AsyncSession,
        embedding_svc: Optional[EmbeddingService] = None,
        model_name: Optional[str] = None
    ):
        super().__init__(agent_name="RetrievalAgent", model_name=model_name)
        self.session = session
        self.embedding_svc = embedding_svc or embedding_service
        self.retriever_repo = VectorRetrieverRepository(session=self.session)

    async def run(
        self,
        structured_input: InputAnalysisOutput,
        top_k: int = 5,
        document_type_filter: Optional[str] = None,
    ) -> RetrievalAgentResult:
        """Formulate semantic query, embed it, and query pgvector."""
        # 1. Synthesize optimized search query using Gemini
        prompt = (
            f"Report Type: {structured_input.report_type}\n"
            f"Company: {structured_input.company or 'N/A'}\n"
            f"Department: {structured_input.department or 'N/A'}\n"
            f"Topics: {', '.join(structured_input.topics) if structured_input.topics else 'General'}\n"
            f"Additional Info: {'; '.join(structured_input.additional_information) if structured_input.additional_information else 'None'}\n"
            f"\nGenerate a dense semantic query to retrieve reference report structures, tone, and technical session patterns."
        )

        query_plan = self._call_gemini_json(
            prompt=prompt,
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.2,
        )

        search_query = query_plan.get("search_query") or f"{structured_input.report_type} { ' '.join(structured_input.topics) }"
        focus_areas = query_plan.get("focus_areas", [])

        # 2. Generate embedding for the search query
        query_vector = self.embedding_svc.generate_embedding(search_query)

        # 3. Vector similarity search in PostgreSQL + pgvector
        retrieved_chunks = await self.retriever_repo.search_similar_chunks(
            query_vector=query_vector,
            top_k=top_k,
            document_type=document_type_filter or structured_input.report_type,
        )

        # 4. Build consolidated context string for subsequent agents
        context_parts = []
        for i, ref in enumerate(retrieved_chunks, 1):
            context_parts.append(
                f"[Reference {i} - '{ref.document_title}' (Score: {ref.similarity_score})]\n{ref.content}"
            )
        summary_context = "\n\n".join(context_parts) if context_parts else "No direct reference chunks found in vector database."

        return RetrievalAgentResult(
            search_query=search_query,
            focus_areas=focus_areas,
            retrieved_chunks=retrieved_chunks,
            summary_context=summary_context,
        )
