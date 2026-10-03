"""Document ingestion service coordinating text extraction, cleaning, chunking, embedding, and pgvector persistence."""

import os
import uuid
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.config import settings
from app.db.models import ReferenceDocument, DocumentChunk
from app.rag.document_loader import DocumentLoader
from app.rag.chunker import TextChunker
from app.rag.embeddings import EmbeddingService, embedding_service
from app.schemas.reference_document import ReferenceDocumentCreate

logger = logging.getLogger(__name__)


class DocumentIngestionService:
    """End-to-end ingestion pipeline from file upload to pgvector storage."""

    def __init__(
        self,
        session: AsyncSession,
        embedding_svc: Optional[EmbeddingService] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ):
        self.session = session
        self.embedding_svc = embedding_svc or embedding_service
        self.chunker = TextChunker(
            chunk_size=chunk_size or settings.DEFAULT_CHUNK_SIZE,
            chunk_overlap=chunk_overlap or settings.DEFAULT_CHUNK_OVERLAP,
        )

    async def ingest_document(
        self,
        file_path: str,
        title: str,
        document_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ReferenceDocument:
        """Run complete document ingestion pipeline."""
        logger.info(f"Starting ingestion for file: {file_path} (Type: {document_type})")

        # 1. Text Extraction & Cleaning
        raw_text, doc_info = DocumentLoader.load_document(file_path)
        if not raw_text.strip():
            raise ValueError(f"No readable text could be extracted from {file_path}")

        # Merge metadata
        merged_metadata = {
            **(metadata or {}),
            **doc_info,
            "title": title,
            "document_type": document_type,
            "file_name": os.path.basename(file_path),
        }

        # 2. Chunking
        chunks = self.chunker.chunk_document(raw_text, document_metadata=merged_metadata)
        logger.info(f"Generated {len(chunks)} chunks for '{title}'")

        if not chunks:
            raise ValueError("Document yielded 0 chunks.")

        # 3. Create ReferenceDocument DB record
        doc_record = ReferenceDocument(
            title=title,
            file_name=os.path.basename(file_path),
            file_path=file_path,
            document_type=document_type,
            metadata_=merged_metadata,
        )
        self.session.add(doc_record)
        await self.session.commit()
        await self.session.refresh(doc_record)

        # 4. Batch Embedding Generation
        chunk_texts = [c.content for c in chunks]
        embeddings = self.embedding_svc.generate_embeddings_batch(chunk_texts)

        # 5. Insert DocumentChunks into pgvector
        chunk_records = []
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            chunk_record = DocumentChunk(
                document_id=doc_record.id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                embedding=emb,
                metadata_={
                    **chunk.metadata,
                    "document_id": str(doc_record.id),
                    "document_title": doc_record.title,
                },
            )
            chunk_records.append(chunk_record)

        self.session.add_all(chunk_records)
        await self.session.commit()

        logger.info(f"Successfully stored {len(chunk_records)} chunks in pgvector for document {doc_record.id}")
        return doc_record

    async def list_documents(self, document_type: Optional[str] = None) -> List[ReferenceDocument]:
        """List ingested reference documents."""
        stmt = select(ReferenceDocument)
        if document_type:
            stmt = stmt.where(ReferenceDocument.document_type == document_type)
        stmt = stmt.order_by(ReferenceDocument.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_document_chunks(self, document_id: uuid.UUID) -> List[DocumentChunk]:
        """Fetch all chunks belonging to a document."""
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_document(self, document_id: uuid.UUID) -> bool:
        """Delete reference document and cascaded chunks."""
        stmt = select(ReferenceDocument).where(ReferenceDocument.id == document_id)
        result = await self.session.execute(stmt)
        doc = result.scalar_one_or_none()
        if not doc:
            return False

        # Clean file on disk if exists
        if os.path.exists(doc.file_path):
            try:
                os.remove(doc.file_path)
            except Exception as e:
                logger.warning(f"Could not remove local file {doc.file_path}: {e}")

        await self.session.delete(doc)
        await self.session.commit()
        return True
