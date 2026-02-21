"""
Schemas Pydantic para entrada e saída da API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Vaga
# ─────────────────────────────────────────────────────────────────────────────
class PontuacaoSchema(BaseModel):
    score: float
    similaridade: float
    score_palavras: float
    complexity_score: int
    dias_estimados: int
    valor_sugerido: float
    motivo_match: dict
    proposta_sugerida: str
    calculado_em: datetime

    model_config = {"from_attributes": True}


class CandidaturaSchema(BaseModel):
    status: str
    valor_final: float | None
    prazo_final: int | None
    notas: str
    atualizado_em: datetime

    model_config = {"from_attributes": True}


class VagaSchema(BaseModel):
    id: int
    fonte: str
    url: str
    titulo: str
    descricao: str
    orcamento_raw: str
    publicado_em: datetime | None
    tags: list[str]
    criado_em: datetime
    pontuacao: PontuacaoSchema | None = None
    candidatura: CandidaturaSchema | None = None

    model_config = {"from_attributes": True}


class VagaListaSchema(BaseModel):
    """Versão resumida para listagem."""
    id: int
    fonte: str
    url: str
    titulo: str
    orcamento_raw: str
    publicado_em: datetime | None
    criado_em: datetime
    score: float | None = None
    complexity_score: int | None = None
    valor_sugerido: float | None = None
    status: str | None = None

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Status / Final
# ─────────────────────────────────────────────────────────────────────────────
class AtualizarStatusInput(BaseModel):
    status: str = Field(..., pattern="^(encontrado|candidatei|em_conversa|aceita|recusada|concluida)$")


class AtualizarFinalInput(BaseModel):
    valor_final: float = Field(..., gt=0)
    prazo_final: int = Field(..., gt=0)


# ─────────────────────────────────────────────────────────────────────────────
# Stats
# ─────────────────────────────────────────────────────────────────────────────
class StatsSchema(BaseModel):
    total_vagas: int
    novas_hoje: int
    candidaturas_ativas: int
    aceitas: int
    concluidas: int
    score_medio: float
    por_fonte: dict[str, int]
    por_status: dict[str, int]


# ─────────────────────────────────────────────────────────────────────────────
# Configurações
# ─────────────────────────────────────────────────────────────────────────────
class ConfigSchema(BaseModel):
    diaria_base: float
    threshold_score: float
    freq_minutos: int
    github_refresh_horas: int
    keywords_boost: list[str]
    keywords_penalty: list[str]
    pisos_por_categoria: dict[str, float]
    atualizado_em: datetime

    model_config = {"from_attributes": True}


class AtualizarConfigInput(BaseModel):
    diaria_base: float | None = None
    threshold_score: float | None = None
    freq_minutos: int | None = None
    github_refresh_horas: int | None = None
    keywords_boost: list[str] | None = None
    keywords_penalty: list[str] | None = None
    pisos_por_categoria: dict[str, float] | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Execuções (runs)
# ─────────────────────────────────────────────────────────────────────────────
class ExecucaoSchema(BaseModel):
    id: int
    iniciado_em: datetime
    finalizado_em: datetime | None
    fontes_verificadas: list[str]
    novas_vagas: int
    vagas_notificadas: int
    erros: dict
    caminho_historico: str
    perfil_reconstruido: bool

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Paginação genérica
# ─────────────────────────────────────────────────────────────────────────────
class PaginaSchema(BaseModel):
    pagina: int
    por_pagina: int
    total: int
    itens: list[Any]
