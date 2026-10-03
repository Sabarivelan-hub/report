"""Pydantic schemas for Reference Documents and Chunks."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    document_type: str = "general"
    title: Optional[str] = None
    department: Optional[str] = None
    year: Optional[int] = None
    source: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class ReferenceDocumentCreate(BaseModel):
    title: str = Field(..., max_length=255)
    file_name: str = Field(..., max_length=255)
    file_path: str = Field(..., max_length=500)
    document_type: str = Field(..., max_length=100)
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)


class DocumentChunkOut(BaseModel):
    id: UUID
    chunk_index: int
    content: str
    metadata: Dict[str, Any]
    similarity_score: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReferenceDocumentOut(BaseModel):
    id: UUID
    title: str
    file_name: str
    file_path: str
    document_type: str
    metadata_: Dict[str, Any] = Field(alias="metadata")
    created_at: datetime
    chunk_count: Optional[int] = 0

    class Config:
        from_attributes = True
        populate_by_name = True
