"""FastAPI dependencies."""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db

# Re-export get_db for convenient import across routers
__all__ = ["get_db"]
