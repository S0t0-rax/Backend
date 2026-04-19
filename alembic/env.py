"""
Alembic env.py — Soporte async PostgreSQL + PostGIS.
"""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings

# Importar TODOS los modelos para que Alembic los detecte
from app.models import *  # noqa: F401, F403
from app.models.base import Base

config = context.config

# Usa la URL SYNC de Alembic (psycopg2) para el modo offline
# y la URL ASYNC (asyncpg) para el modo online
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL_SYNC)

if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Modo offline — genera SQL sin conexión a la BD."""
    context.configure(
        url=settings.DATABASE_URL_SYNC,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Modo online — conexión async con asyncpg."""
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = settings.DATABASE_URL  # asyncpg

    connectable = async_engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
