"""FastAPI Application Entry Point."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.db.database import async_engine, Base
from app.api.v1.documents import router as documents_router
from app.api.v1.templates import router as templates_router
from app.api.v1.reports import router as reports_router

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("intellireport")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for database initialization and cleanup."""
    logger.info("Starting up IntelliReport AI Backend...")
    # Initialize pgvector extension and create tables if not present
    async with async_engine.begin() as conn:
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            logger.info("Verified pgvector extension.")
        except Exception as e:
            logger.warning(f"Note on pgvector extension check: {e}")

        # In dev mode, auto-create tables if running without Alembic
        if settings.DEBUG:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Initialized database tables.")

    yield
    logger.info("Shutting down IntelliReport AI Backend...")
    await async_engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-grade AI Report Generation Backend powered by Google Gemini, pgvector, and Multi-Agent Orchestration.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=f"{settings.API_V1_STR}/docs",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(documents_router, prefix=settings.API_V1_STR)
app.include_router(templates_router, prefix=settings.API_V1_STR)
app.include_router(reports_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health"])
async def health_check():
    """Healthcheck endpoint for Kubernetes / Cloud Run / Load Balancers."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "database": "postgresql+pgvector",
        "gemini_model": settings.GEMINI_GENERATION_MODEL,
        "embedding_model": settings.GEMINI_EMBEDDING_MODEL,
    }
