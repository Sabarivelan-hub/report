"""001_initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector
from pgvector.sqlalchemy import Vector

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0. Ensure pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 1. users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # 2. report_templates table
    op.create_table(
        'report_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('report_type', sa.String(length=100), nullable=False),
        sa.Column('template_structure', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_report_templates_report_type', 'report_templates', ['report_type'])

    # 3. reference_documents table
    op.create_table(
        'reference_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('document_type', sa.String(length=100), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_reference_documents_document_type', 'reference_documents', ['document_type'])

    # 4. document_chunks table with pgvector column
    op.create_table(
        'document_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('reference_documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(768), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_document_chunks_document_id', 'document_chunks', ['document_id'])
    op.create_index('idx_document_chunks_doc_chunk', 'document_chunks', ['document_id', 'chunk_index'])

    # HNSW Index for cosine similarity vector search
    op.execute(
        "CREATE INDEX idx_document_chunks_embedding_hnsw ON document_chunks "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);"
    )

    # 5. generated_reports table
    op.create_table(
        'generated_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('report_type', sa.String(length=100), nullable=False),
        sa.Column('input_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('final_content', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_generated_reports_report_type', 'generated_reports', ['report_type'])
    op.create_index('ix_generated_reports_status', 'generated_reports', ['status'])
    op.create_index('ix_generated_reports_user_id', 'generated_reports', ['user_id'])

    # 6. report_versions table
    op.create_table(
        'report_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('generated_reports.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('content', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('validation_result', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_report_versions_report_id', 'report_versions', ['report_id'])
    op.create_index('idx_report_versions_rep_ver', 'report_versions', ['report_id', 'version_number'], unique=True)

    # 7. generation_logs table
    op.create_table(
        'generation_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('generated_reports.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_name', sa.String(length=100), nullable=False),
        sa.Column('input_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('output_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('execution_time', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_generation_logs_report_id', 'generation_logs', ['report_id'])
    op.create_index('ix_generation_logs_agent_name', 'generation_logs', ['agent_name'])
    op.create_index('ix_generation_logs_created_at', 'generation_logs', ['created_at'])


def downgrade() -> None:
    op.drop_table('generation_logs')
    op.drop_table('report_versions')
    op.drop_table('generated_reports')
    op.drop_table('document_chunks')
    op.drop_table('reference_documents')
    op.drop_table('report_templates')
    op.drop_table('users')
