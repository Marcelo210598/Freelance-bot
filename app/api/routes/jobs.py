"""
Endpoints relacionados às vagas.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from pydantic import BaseModel

from app.api.middleware import verificar_token
from app.api.schemas import (
    AtualizarFinalInput,
    AtualizarStatusInput,
    PaginaSchema,
    VagaListaSchema,
    VagaSchema,
)
from app.core.database import obter_sessao
from app.core.models import Candidatura, PontuacaoVaga, StatusCandidatura, Vaga


class CandidaturaResp(BaseModel):
    vaga_id: int
    status: str


roteador = APIRouter(prefix="/api/jobs", tags=["vagas"])
TokenDep = Annotated[str, Depends(verificar_token)]
SessaoDep = Annotated[AsyncSession, Depends(obter_sessao)]


@roteador.get("", response_model=PaginaSchema)
async def listar_vagas(
    _token: TokenDep,
    sessao: SessaoDep,
    status_filtro: str | None = Query(None, alias="status"),
    fonte: str | None = None,
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    q: str | None = None,
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
) -> PaginaSchema:
    """Lista vagas com filtros, paginação e scores."""
    consulta = (
        select(Vaga)
        .options(joinedload(Vaga.pontuacao), joinedload(Vaga.candidatura))
        .order_by(PontuacaoVaga.score.desc().nullslast(), Vaga.criado_em.desc())
        .outerjoin(Vaga.pontuacao)
        .outerjoin(Vaga.candidatura)
    )

    if fonte:
        consulta = consulta.where(Vaga.fonte == fonte)
    if min_score > 0:
        consulta = consulta.where(PontuacaoVaga.score >= min_score)
    if status_filtro:
        consulta = consulta.where(Candidatura.status == status_filtro)
    if q:
        termo = f"%{q.lower()}%"
        consulta = consulta.where(
            Vaga.titulo.ilike(termo) | Vaga.descricao.ilike(termo)
        )

    # conta total
    total_query = select(func.count()).select_from(consulta.subquery())
    total = (await sessao.execute(total_query)).scalar_one()

    # aplica paginação
    consulta = consulta.offset((pagina - 1) * por_pagina).limit(por_pagina)
    resultado = await sessao.execute(consulta)
    vagas = resultado.unique().scalars().all()

    itens = []
    for v in vagas:
        item = VagaListaSchema(
            id=v.id,
            fonte=v.fonte,
            url=v.url,
            titulo=v.titulo,
            orcamento_raw=v.orcamento_raw,
            publicado_em=v.publicado_em,
            criado_em=v.criado_em,
            score=v.pontuacao.score if v.pontuacao else None,
            complexity_score=v.pontuacao.complexity_score if v.pontuacao else None,
            valor_sugerido=v.pontuacao.valor_sugerido if v.pontuacao else None,
            status=v.candidatura.status if v.candidatura else "encontrado",
        )
        itens.append(item)

    return PaginaSchema(pagina=pagina, por_pagina=por_pagina, total=total, itens=itens)


@roteador.get("/{vaga_id}", response_model=VagaSchema)
async def detalhar_vaga(
    vaga_id: int,
    _token: TokenDep,
    sessao: SessaoDep,
) -> VagaSchema:
    """Retorna todos os dados de uma vaga, incluindo proposta sugerida."""
    resultado = await sessao.execute(
        select(Vaga)
        .options(joinedload(Vaga.pontuacao), joinedload(Vaga.candidatura))
        .where(Vaga.id == vaga_id)
    )
    vaga = resultado.unique().scalar_one_or_none()
    if not vaga:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vaga não encontrada.")
    return VagaSchema.model_validate(vaga)


@roteador.patch("/{vaga_id}/status", response_model=CandidaturaResp)
async def atualizar_status(
    vaga_id: int,
    dados: AtualizarStatusInput,
    _token: TokenDep,
    sessao: SessaoDep,
) -> dict:
    """Atualiza o status da candidatura de uma vaga."""
    resultado = await sessao.execute(
        select(Candidatura).where(Candidatura.vaga_id == vaga_id)
    )
    cand = resultado.scalar_one_or_none()

    if not cand:
        # cria candidatura se não existir
        cand = Candidatura(vaga_id=vaga_id, status=dados.status)
        sessao.add(cand)
    else:
        cand.status = dados.status

    await sessao.commit()
    return {"vaga_id": vaga_id, "status": cand.status}


@roteador.patch("/{vaga_id}/final")
async def atualizar_final(
    vaga_id: int,
    dados: AtualizarFinalInput,
    _token: TokenDep,
    sessao: SessaoDep,
) -> dict:
    """Registra valor e prazo finais acordados."""
    resultado = await sessao.execute(
        select(Candidatura).where(Candidatura.vaga_id == vaga_id)
    )
    cand = resultado.scalar_one_or_none()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidatura não encontrada.")

    cand.valor_final = dados.valor_final
    cand.prazo_final = dados.prazo_final
    await sessao.commit()
    return {"vaga_id": vaga_id, "valor_final": cand.valor_final, "prazo_final": cand.prazo_final}


