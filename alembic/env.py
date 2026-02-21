"""
Configuração do Alembic para migrações assíncronas com Neon Postgres.
"""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# importa todos os modelos para que o Alembic os detecte
from app.core.database import Base
import app.core.models  # noqa: F401 — necessário para registrar os modelos

config = context.config

# Sobrepõe a URL com a variável de ambiente
config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def rodar_migracao_offline() -> None:
    """Gera SQL sem conectar ao banco."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
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
    """Executa migrações com engine assíncrono."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(rodar_migracao_sync)
    await connectable.dispose()


if context.is_offline_mode():
    rodar_migracao_offline()
else:
    asyncio.run(rodar_migracao_online())
