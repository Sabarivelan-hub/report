"""SQLAlchemy ORM models for IntelliReport database."""

from datetime import datetime
from typing import Optional, List, Any
import uuid

from sqlalchemy import (
    String,
    Text,
    DateTime,
    ForeignKey,
    Integer,
    Float,
    Index,
    func
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.db.database import Base


class User(Base):
    """Users table."""
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    reports: Mapped[List["GeneratedReport"]] = relationship(
        "GeneratedReport", back_populates="user", cascade="all, delete-orphan"
    )


class ReportTemplate(Base):
    """Report templates table defining standard structures and instructions."""
    __tablename__ = "report_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    report_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    template_structure: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ReferenceDocument(Base):
    """Uploaded reference reports and knowledge documents for RAG."""
    __tablename__ = "reference_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    document_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    chunks: Mapped[List["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    """Text chunks with embeddings for vector similarity search."""
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reference_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[List[float]] = mapped_column(Vector(768), nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    document: Mapped["ReferenceDocument"] = relationship(
        "ReferenceDocument", back_populates="chunks"
    )

    # Table arguments: HNSW index on vector embedding for high-speed cosine similarity search
    __table_args__ = (
        Index(
            "idx_document_chunks_embedding_hnsw",
            embedding,
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"}
        ),
        Index("idx_document_chunks_doc_chunk", "document_id", "chunk_index"),
    )


class GeneratedReport(Base):
    """Generated reports representing the overall generation task."""
    __tablename__ = "generated_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    report_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    input_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    final_content: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="pending", index=True, nullable=False
    )  # pending, analyzing, retrieving, planning, generating, validating, completed, failed
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="reports")
    versions: Mapped[List["ReportVersion"]] = relationship(
        "ReportVersion", back_populates="report", cascade="all, delete-orphan", order_by="ReportVersion.version_number"
    )
    logs: Mapped[List["GenerationLog"]] = relationship(
        "GenerationLog", back_populates="report", cascade="all, delete-orphan", order_by="GenerationLog.created_at"
    )


class ReportVersion(Base):
    """Versions of the report generated across regeneration cycles."""
    __tablename__ = "report_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("generated_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    validation_result: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    report: Mapped["GeneratedReport"] = relationship(
        "GeneratedReport", back_populates="versions"
    )

    __table_args__ = (
        Index("idx_report_versions_rep_ver", "report_id", "version_number", unique=True),
    )


class GenerationLog(Base):
    """Detailed audit logs for every individual agent step in the orchestrator pipeline."""
    __tablename__ = "generation_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("generated_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    input_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    output_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    execution_time: Mapped[float] = mapped_column(Float, nullable=False)  # in seconds / ms
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # success, failure, retry
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationships
    report: Mapped["GeneratedReport"] = relationship(
        "GeneratedReport", back_populates="logs"
    )
