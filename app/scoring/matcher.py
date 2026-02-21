"""
Cálculo de score de match entre perfil e vaga.

Score final = 0.7 * similaridade_cosseno + 0.3 * score_palavras
(pesos configuráveis)

score_palavras: soma de boost/penalty normalizada em [-0.3, +0.3]
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import numpy as np

from app.coletores.base import VagaColetada
from app.perfil.embeddings import (
    deserializar_embedding,
    gerar_embedding,
    similaridade_cosseno,
)

logger = logging.getLogger(__name__)

PESO_SIMILARIDADE = 0.70
PESO_PALAVRAS = 0.30


@dataclass
class ResultadoMatch:
    score: float            # 0.0 – 1.0
    similaridade: float
    score_palavras: float
    motivo_match: dict      # {"bullets": [...], "resumo": "..."}


def calcular_score(
    vaga: VagaColetada,
    embedding_perfil: np.ndarray,
    keywords_boost: list[str],
    keywords_penalty: list[str],
) -> ResultadoMatch:
    """
    Calcula o score de match para uma vaga.
    """
    texto_vaga = _montar_texto_vaga(vaga)

    # ── similaridade semântica ────────────────────────────────────────────
    try:
        embedding_vaga = gerar_embedding(texto_vaga)
        similaridade = max(0.0, similaridade_cosseno(embedding_perfil, embedding_vaga))
    except Exception as exc:
        logger.warning("[matcher] Erro ao gerar embedding: %s", exc)
        similaridade = 0.0

    # ── score por palavras-chave ──────────────────────────────────────────
    texto_lower = texto_vaga.lower()
    boosts_encontrados: list[str] = []
    penalties_encontradas: list[str] = []

    for kw in keywords_boost:
        if re.search(r"\b" + re.escape(kw.lower()) + r"\b", texto_lower):
            boosts_encontrados.append(kw)

    for kw in keywords_penalty:
        if re.search(r"\b" + re.escape(kw.lower()) + r"\b", texto_lower):
            penalties_encontradas.append(kw)

    # normalização: cada boost +0.05, cada penalty -0.08 (máx ±0.3)
    raw_palavras = (len(boosts_encontrados) * 0.05) - (len(penalties_encontradas) * 0.08)
    score_palavras = max(-0.3, min(0.3, raw_palavras))

    # ── score final ───────────────────────────────────────────────────────
    score = (PESO_SIMILARIDADE * similaridade) + (PESO_PALAVRAS * (score_palavras + 0.3) / 0.6)
    score = max(0.0, min(1.0, score))

    # ── motivo do match ───────────────────────────────────────────────────
    bullets = []
    if boosts_encontrados:
        bullets.append(f"Tecnologias alinhadas: {', '.join(boosts_encontrados[:5])}")
    if similaridade > 0.6:
        bullets.append("Descrição muito similar ao seu perfil profissional")
    elif similaridade > 0.4:
        bullets.append("Descrição moderadamente alinhada ao seu perfil")
    if penalties_encontradas:
        bullets.append(f"⚠️ Penalidade: tecnologias fora do perfil ({', '.join(penalties_encontradas[:3])})")
    if not bullets:
        bullets.append("Match baseado em similaridade semântica geral")

    resumo = f"Score {score:.0%} — {len(boosts_encontrados)} tech alinhada(s)"

    return ResultadoMatch(
        score=round(score, 4),
        similaridade=round(similaridade, 4),
        score_palavras=round(score_palavras, 4),
        motivo_match={"bullets": bullets, "resumo": resumo},
    )


def _montar_texto_vaga(vaga: VagaColetada) -> str:
    """Concatena campos relevantes da vaga para embedding."""
    partes = [vaga.titulo]
    if vaga.descricao:
        partes.append(vaga.descricao)
    if vaga.tags:
        partes.append(" ".join(vaga.tags))
    return " ".join(partes)


def calcular_scores_lote(
    vagas: list[VagaColetada],
    embedding_perfil_b64: str,
    keywords_boost: list[str],
    keywords_penalty: list[str],
) -> list[tuple[VagaColetada, ResultadoMatch]]:
    """
    Calcula scores para uma lista de vagas.
    Retorna lista de (vaga, resultado).
    """
    try:
        embedding_perfil = deserializar_embedding(embedding_perfil_b64)
    except Exception as exc:
        logger.error("[matcher] Erro ao deserializar embedding do perfil: %s", exc)
        return []

    resultados = []
    for vaga in vagas:
        resultado = calcular_score(vaga, embedding_perfil, keywords_boost, keywords_penalty)
        resultados.append((vaga, resultado))

    return resultados
