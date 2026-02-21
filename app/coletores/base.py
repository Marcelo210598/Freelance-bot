"""
Classe base para todos os coletores de vagas.
Define interface, retry com backoff, rate-limit e cache simples.
"""

from __future__ import annotations

import hashlib
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Dataclass normalizado de vaga
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class VagaColetada:
    fonte: str
    external_id: str
    url: str
    titulo: str
    descricao: str = ""
    orcamento_raw: str = ""
    publicado_em: datetime | None = None
    tags: list[str] = field(default_factory=list)
    raw_json: dict[str, Any] = field(default_factory=dict)

    def chave_deduplicacao(self) -> str:
        """Hash único para deduplicação: fonte + external_id."""
        return hashlib.sha256(f"{self.fonte}:{self.external_id}".encode()).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# Cache em memória simples (TTL por chave)
# ─────────────────────────────────────────────────────────────────────────────
class CacheMemoria:
    def __init__(self, ttl_segundos: int = 3600):
        self._dados: dict[str, tuple[Any, float]] = {}
        self._ttl = ttl_segundos

    def obter(self, chave: str) -> Any | None:
        entrada = self._dados.get(chave)
        if not entrada:
            return None
        valor, timestamp = entrada
        if time.time() - timestamp > self._ttl:
            del self._dados[chave]
            return None
        return valor

    def salvar(self, chave: str, valor: Any) -> None:
        self._dados[chave] = (valor, time.time())


_cache_global = CacheMemoria(ttl_segundos=1800)  # 30 min


# ─────────────────────────────────────────────────────────────────────────────
# Coletor base
# ─────────────────────────────────────────────────────────────────────────────
class ColetorBase(ABC):
    """
    Interface comum para todos os coletores.
    Subclasses implementam apenas `_coletar_paginas()`.
    """

    nome: str = "base"
    intervalo_entre_requisicoes: float = 3.0  # segundos entre requests (ser gentil)

    def __init__(self) -> None:
        self._cliente = httpx.AsyncClient(
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; FreelanceBot/1.0; "
                    "+https://github.com/Marcelo210598/Freelance-bot)"
                ),
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            },
            follow_redirects=True,
            timeout=30.0,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self._cliente.aclose()

    @abstractmethod
    async def _coletar_paginas(self) -> list[VagaColetada]:
        """Lógica específica de cada fonte. Retorna lista de vagas normalizadas."""
        ...

    async def coletar(self) -> list[VagaColetada]:
        """Método público. Chama _coletar_paginas com tratamento de erros."""
        logger.info("[%s] Iniciando coleta...", self.nome)
        try:
            vagas = await self._coletar_paginas()
            logger.info("[%s] %d vagas coletadas.", self.nome, len(vagas))
            return vagas
        except Exception as exc:
            logger.error("[%s] Erro na coleta: %s", self.nome, exc, exc_info=True)
            return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=30),
        retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
        reraise=True,
    )
    async def _get(self, url: str, **kwargs) -> httpx.Response:
        """GET com retry automático e rate-limit."""
        logger.debug("[%s] GET %s", self.nome, url)
        resposta = await self._cliente.get(url, **kwargs)
        resposta.raise_for_status()
        await self._esperar()
        return resposta

    async def _esperar(self) -> None:
        """Rate-limit: aguarda entre requisições."""
        import asyncio
        await asyncio.sleep(self.intervalo_entre_requisicoes)
