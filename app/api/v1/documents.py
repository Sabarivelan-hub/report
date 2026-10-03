"""API endpoints for Reference Document Ingestion and Chunk Inspection."""

import os
import shutil
import tempfile
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services.document_service import DocumentIngestionService
from app.schemas.reference_document import ReferenceDocumentOut, DocumentChunkOut

router = APIRouter(prefix="/documents", tags=["Reference Documents"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/intellireport_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/ingest", response_model=ReferenceDocumentOut, status_code=status.HTTP_201_CREATED)
async def ingest_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    document_type: str = Form(...),
    department: Optional[str] = Form(None),
    year: Optional[int] = Form(None),
    chunk_size: Optional[int] = Form(None),
    chunk_overlap: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Ingest a reference PDF or DOCX report into pgvector.
    Extracts text, cleans formatting, segments into chunks with overlap,
    generates embeddings via Gemini text-embedding-004, and stores in PostgreSQL.
    """
    allowed_exts = [".pdf", ".docx", ".doc", ".txt", ".md"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{file_ext}'. Allowed formats: {', '.join(allowed_exts)}"
        )

    # Save to disk
    temp_filename = f"{uuid.uuid4()}_{file.filename}"
    temp_filepath = os.path.join(UPLOAD_DIR, temp_filename)

    with open(temp_filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        service = DocumentIngestionService(
            session=db,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        metadata = {
            "department": department,
            "year": year,
            "original_filename": file.filename,
        }

        doc = await service.ingest_document(
            file_path=temp_filepath,
            title=title,
            document_type=document_type,
            metadata=metadata,
        )

        chunks = await service.get_document_chunks(doc.id)
        return ReferenceDocumentOut(
            id=doc.id,
            title=doc.title,
            file_name=doc.file_name,
            file_path=doc.file_path,
            document_type=doc.document_type,
            metadata=doc.metadata_,
            created_at=doc.created_at,
            chunk_count=len(chunks),
        )

    except Exception as e:
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("", response_model=List[ReferenceDocumentOut])
async def list_documents(
    document_type: Optional[str] = Query(None, description="Filter by report document type"),
    db: AsyncSession = Depends(get_db),
):
    """List all ingested reference knowledge documents."""
    service = DocumentIngestionService(session=db)
    docs = await service.list_documents(document_type=document_type)

    results = []
    for doc in docs:
        chunks = await service.get_document_chunks(doc.id)
        results.append(
            ReferenceDocumentOut(
                id=doc.id,
                title=doc.title,
                file_name=doc.file_name,
                file_path=doc.file_path,
                document_type=doc.document_type,
                metadata=doc.metadata_,
                created_at=doc.created_at,
                chunk_count=len(chunks),
            )
        )
    return results


@router.get("/{document_id}/chunks", response_model=List[DocumentChunkOut])
async def get_document_chunks(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Inspect the chunks and metadata extracted for a given reference document."""
    service = DocumentIngestionService(session=db)
    chunks = await service.get_document_chunks(document_id=document_id)
    return [
        DocumentChunkOut(
            id=c.id,
            chunk_index=c.chunk_index,
            content=c.content,
            metadata=c.metadata_,
            created_at=c.created_at,
        )
        for c in chunks
    ]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a reference document and all associated vector embeddings."""
    service = DocumentIngestionService(session=db)
    success = await service.delete_document(document_id=document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Reference document not found")
