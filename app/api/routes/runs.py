"""
Endpoint para histórico de execuções do worker.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware import verificar_token
from app.api.schemas import ExecucaoSchema, PaginaSchema
from app.core.database import obter_sessao
from app.core.models import Execucao

roteador = APIRouter(prefix="/api/runs", tags=["execuções"])
TokenDep = Annotated[str, Depends(verificar_token)]
SessaoDep = Annotated[AsyncSession, Depends(obter_sessao)]


@roteador.get("", response_model=PaginaSchema)
async def listar_execucoes(
    _token: TokenDep,
    sessao: SessaoDep,
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
) -> PaginaSchema:
    """Retorna histórico de execuções mais recentes primeiro."""
    from sqlalchemy import func

    total = (await sessao.execute(select(func.count(Execucao.id)))).scalar_one()

    resultado = await sessao.execute(
        select(Execucao)
        .order_by(Execucao.iniciado_em.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
    )
    execucoes = resultado.scalars().all()

    return PaginaSchema(
        pagina=pagina,
        por_pagina=por_pagina,
        total=total,
        itens=[ExecucaoSchema.model_validate(e) for e in execucoes],
    )
