import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import target metadata from models
from app.db.database import Base
import app.db.models  # Ensure all models are registered
from app.core.config import settings

config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Use DATABASE_URL from environment if available
database_url = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
# Replace asyncpg with psycopg2 for standard synchronous Alembic operations
if database_url and database_url.startswith("postgresql+asyncpg"):
    database_url = database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")

config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Enable pgvector extension before running migrations
        connection.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector;"))
        connection.commit()

        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
