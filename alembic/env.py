"""
Configuração do Alembic para migrações assíncronas com Neon Postgres.
"""

import asyncio
import os
from logging.config import fileConfig

from dotenv import load_dotenv
load_dotenv()  # carrega o .env antes de ler os environ

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

# importa todos os modelos para que o Alembic os detecte
from app.core.database import Base
import app.core.models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

DATABASE_URL = os.environ["DATABASE_URL"]


def rodar_migracao_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def rodar_migracao_sync(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def rodar_migracao_online() -> None:
    connectable = create_async_engine(
        DATABASE_URL,
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(rodar_migracao_sync)
    await connectable.dispose()


if context.is_offline_mode():
    rodar_migracao_offline()
else:
    asyncio.run(rodar_migracao_online())
