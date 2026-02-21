"""
Configuração do banco de dados (SQLAlchemy assíncrono + Neon Postgres).
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import obter_config

cfg = obter_config()

# Engine assíncrono; pool_pre_ping evita conexões mortas no Neon
engine = create_async_engine(
    cfg.database_url,
    echo=cfg.env == "development",
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

FabricaSessao = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base declarativa compartilhada por todos os modelos."""
    pass


async def obter_sessao():
    """Dependência do FastAPI: abre sessão e garante fechamento."""
    async with FabricaSessao() as sessao:
        yield sessao
