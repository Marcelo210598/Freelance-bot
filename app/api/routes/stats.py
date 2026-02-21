"""
Endpoint de estatísticas gerais (KPIs do dashboard).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware import verificar_token
from app.api.schemas import StatsSchema
from app.core.database import obter_sessao
from app.core.models import Candidatura, PontuacaoVaga, Vaga

roteador = APIRouter(prefix="/api/stats", tags=["stats"])
TokenDep = Annotated[str, Depends(verificar_token)]
SessaoDep = Annotated[AsyncSession, Depends(obter_sessao)]


@roteador.get("", response_model=StatsSchema)
async def obter_stats(_token: TokenDep, sessao: SessaoDep) -> StatsSchema:
    """KPIs gerais para o painel de overview."""
    hoje = datetime.now(timezone.utc).date()

    # total de vagas
    total = (await sessao.execute(select(func.count(Vaga.id)))).scalar_one()

    # novas hoje
    novas_hoje = (
        await sessao.execute(
            select(func.count(Vaga.id)).where(func.date(Vaga.criado_em) == hoje)
        )
    ).scalar_one()

    # por status
    status_rows = (
        await sessao.execute(
            select(Candidatura.status, func.count(Candidatura.id)).group_by(Candidatura.status)
        )
    ).all()
    por_status: dict[str, int] = {r[0]: r[1] for r in status_rows}

    # candidaturas ativas (candidatei + em_conversa)
    candidaturas_ativas = por_status.get("candidatei", 0) + por_status.get("em_conversa", 0)
    aceitas = por_status.get("aceita", 0)
    concluidas = por_status.get("concluida", 0)

    # score médio
    score_medio = (
        await sessao.execute(select(func.avg(PontuacaoVaga.score)))
    ).scalar_one() or 0.0

    # por fonte
    fonte_rows = (
        await sessao.execute(
            select(Vaga.fonte, func.count(Vaga.id)).group_by(Vaga.fonte)
        )
    ).all()
    por_fonte: dict[str, int] = {r[0]: r[1] for r in fonte_rows}

    return StatsSchema(
        total_vagas=total,
        novas_hoje=novas_hoje,
        candidaturas_ativas=candidaturas_ativas,
        aceitas=aceitas,
        concluidas=concluidas,
        score_medio=round(score_medio, 3),
        por_fonte=por_fonte,
        por_status=por_status,
    )
