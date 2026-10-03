"""Retrieval repository and service layer using PostgreSQL + pgvector."""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import DocumentChunk, ReferenceDocument

logger = logging.getLogger(__name__)


class RetrievedReference(BaseModel):
    """Contextual reference chunk retrieved via vector similarity search."""
    chunk_id: UUID
    document_id: UUID
    document_title: str
    document_type: str
    chunk_index: int
    content: str
    similarity_score: float
    metadata: Dict[str, Any]


class VectorRetrieverRepository:
    """Independent database repository layer for vector search over document_chunks."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def search_similar_chunks(
        self,
        query_vector: List[float],
        top_k: int = settings.DEFAULT_TOP_K,
        document_type: Optional[str] = None,
        min_similarity: float = settings.SIMILARITY_THRESHOLD,
    ) -> List[RetrievedReference]:
        """Perform cosine similarity vector search in PostgreSQL using pgvector."""
        try:
            # pgvector provides cosine_distance operator: <=>
            # cosine similarity = 1 - cosine distance
            cosine_distance = DocumentChunk.embedding.cosine_distance(query_vector)

            stmt = (
                select(
                    DocumentChunk.id.label("chunk_id"),
                    DocumentChunk.document_id,
                    DocumentChunk.chunk_index,
                    DocumentChunk.content,
                    DocumentChunk.metadata_.label("chunk_metadata"),
                    ReferenceDocument.title.label("document_title"),
                    ReferenceDocument.document_type,
                    (1.0 - cosine_distance).label("similarity_score")
                )
                .join(ReferenceDocument, DocumentChunk.document_id == ReferenceDocument.id)
            )

            # Optional filter by document type
            conditions = []
            if document_type:
                conditions.append(ReferenceDocument.document_type == document_type)

            if conditions:
                stmt = stmt.where(and_(*conditions))

            # Order by smallest cosine distance (highest similarity)
            stmt = stmt.order_by(cosine_distance.asc()).limit(top_k)

            result = await self.session.execute(stmt)
            rows = result.all()

            references: List[RetrievedReference] = []
            for row in rows:
                score = float(row.similarity_score)
                # Apply optional threshold filter
                if score >= min_similarity:
                    references.append(
                        RetrievedReference(
                            chunk_id=row.chunk_id,
                            document_id=row.document_id,
                            document_title=row.document_title,
                            document_type=row.document_type,
                            chunk_index=row.chunk_index,
                            content=row.content,
                            similarity_score=round(score, 4),
                            metadata=row.chunk_metadata or {},
                        )
                    )

            # If threshold was too restrictive and yielded nothing, return top 2 closest
            if not references and rows:
                top_row = rows[0]
                references.append(
                    RetrievedReference(
                        chunk_id=top_row.chunk_id,
                        document_id=top_row.document_id,
                        document_title=top_row.document_title,
                        document_type=top_row.document_type,
                        chunk_index=top_row.chunk_index,
                        content=top_row.content,
                        similarity_score=round(float(top_row.similarity_score), 4),
                        metadata=top_row.chunk_metadata or {},
                    )
                )

            return references

        except Exception as e:
            logger.error(f"Error executing vector similarity search: {e}")
            raise
