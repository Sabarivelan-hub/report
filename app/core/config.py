"""Application configuration using Pydantic Settings."""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings loaded from environment variables."""

    # Project metadata
    PROJECT_NAME: str = "IntelliReport AI Backend"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # AI / Gemini API
    GEMINI_API_KEY: str
    GEMINI_GENERATION_MODEL: str = "gemini-3.8-flash"
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"
    EMBEDDING_DIMENSION: int = 768

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/intellireport"
    SYNC_DATABASE_URL: Optional[str] = "postgresql+psycopg2://postgres:postgres@localhost:5432/intellireport"

    # RAG & Chunking settings
    DEFAULT_CHUNK_SIZE: int = 800  # characters
    DEFAULT_CHUNK_OVERLAP: int = 150  # characters
    DEFAULT_TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.55

    # Agent Orchestration
    MAX_REGENERATION_ATTEMPTS: int = 2
    AGENT_TIMEOUT_SECONDS: int = 60

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
