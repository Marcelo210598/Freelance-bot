"""
Endpoints de configuração do sistema.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware import verificar_token
from app.api.schemas import AtualizarConfigInput, ConfigSchema
from app.core.database import obter_sessao
from app.core.models import Configuracao

roteador = APIRouter(prefix="/api/settings", tags=["configurações"])
TokenDep = Annotated[str, Depends(verificar_token)]
SessaoDep = Annotated[AsyncSession, Depends(obter_sessao)]


async def _obter_ou_criar_config(sessao: AsyncSession) -> Configuracao:
    """Garante que sempre exista uma linha de configuração (id=1)."""
    cfg = (await sessao.execute(select(Configuracao).where(Configuracao.id == 1))).scalar_one_or_none()
    if not cfg:
        cfg = Configuracao(id=1)
        sessao.add(cfg)
        await sessao.commit()
        await sessao.refresh(cfg)
    return cfg


@roteador.get("", response_model=ConfigSchema)
async def obter_config(_token: TokenDep, sessao: SessaoDep) -> ConfigSchema:
    cfg = await _obter_ou_criar_config(sessao)
    return ConfigSchema.model_validate(cfg)


@roteador.patch("", response_model=ConfigSchema)
async def atualizar_config(
    dados: AtualizarConfigInput,
    _token: TokenDep,
    sessao: SessaoDep,
) -> ConfigSchema:
    """Atualiza apenas os campos enviados (PATCH parcial)."""
    cfg = await _obter_ou_criar_config(sessao)

    alteracoes = dados.model_dump(exclude_none=True)
    for campo, valor in alteracoes.items():
        setattr(cfg, campo, valor)

    await sessao.commit()
    await sessao.refresh(cfg)
    return ConfigSchema.model_validate(cfg)
