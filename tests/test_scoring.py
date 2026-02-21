"""
Testes de scoring e estimativa de valor/prazo.
Não usa banco de dados nem GPU.
"""

from datetime import datetime, timezone

import numpy as np
import pytest

from app.coletores.base import VagaColetada
from app.scoring.estimador import estimar
from app.scoring.matcher import calcular_score


# ── Estimador ─────────────────────────────────────────────────────────────────
PISOS = {"simples": 150.0, "medio": 400.0, "complexo": 900.0, "muito_complexo": 1800.0}


def test_estimador_projeto_simples():
    resultado = estimar(
        titulo="Landing page simples",
        descricao="Criar landing page estática com formulário de contato",
        diaria_base=100.0,
        pisos=PISOS,
    )
    assert resultado.complexity_score <= 35
    assert resultado.categoria in ("simples", "medio")
    assert resultado.valor_sugerido >= PISOS["simples"]


def test_estimador_projeto_complexo():
    resultado = estimar(
        titulo="Sistema ERP completo do zero",
        descricao=(
            "Desenvolver ERP com WebSocket, Docker, deploy CI/CD, "
            "pagamentos Stripe, painel admin, autenticação OAuth2."
        ),
        diaria_base=100.0,
        pisos=PISOS,
    )
    assert resultado.complexity_score > 50
    assert resultado.categoria in ("complexo", "muito_complexo")
    assert resultado.valor_sugerido >= PISOS["complexo"]
    assert resultado.dias_estimados >= 11


def test_estimador_respeita_piso():
    resultado = estimar(
        titulo="Pequena API",
        descricao="api rest simples",
        diaria_base=50.0,  # diária baixa
        pisos=PISOS,
    )
    # valor não pode ser menor que o piso da categoria
    assert resultado.valor_sugerido >= PISOS[resultado.categoria]


def test_estimador_gera_proposta():
    resultado = estimar(
        titulo="Bot Telegram",
        descricao="Bot em Python para automação",
        diaria_base=100.0,
        pisos=PISOS,
    )
    assert len(resultado.proposta) > 50
    assert "Olá" in resultado.proposta
    assert "R$" in resultado.proposta


# ── Matcher (score de keywords sem embeddings reais) ──────────────────────────
def _embedding_falso(dim: int = 384) -> np.ndarray:
    """Vetor aleatório normalizado para testes sem GPU."""
    rng = np.random.default_rng(42)
    v = rng.random(dim).astype(np.float32)
    return v / np.linalg.norm(v)


def _vaga(titulo: str, descricao: str = "", tags: list | None = None) -> VagaColetada:
    return VagaColetada(
        fonte="teste",
        external_id="x",
        url="http://x.com",
        titulo=titulo,
        descricao=descricao,
        tags=tags or [],
        publicado_em=datetime.now(timezone.utc),
    )


def test_score_com_boost():
    """Vaga com keywords de boost deve ter score_palavras positivo."""
    vaga = _vaga("API FastAPI Python", "desenvolver api com postgres e docker")
    embedding_perfil = _embedding_falso()

    resultado = calcular_score(
        vaga=vaga,
        embedding_perfil=embedding_perfil,
        keywords_boost=["fastapi", "python", "postgres", "docker"],
        keywords_penalty=["wordpress"],
    )
    assert resultado.score_palavras > 0
    assert 0 <= resultado.score <= 1


def test_score_com_penalty():
    """Vaga com keywords de penalty deve ter score_palavras negativo."""
    vaga = _vaga("Site WordPress", "criar site wordpress com php e magento")
    embedding_perfil = _embedding_falso()

    resultado = calcular_score(
        vaga=vaga,
        embedding_perfil=embedding_perfil,
        keywords_boost=["fastapi", "python"],
        keywords_penalty=["wordpress", "php", "magento"],
    )
    assert resultado.score_palavras < 0


def test_score_range_valido():
    """Score sempre entre 0 e 1."""
    vaga = _vaga("Qualquer coisa")
    embedding_perfil = _embedding_falso()

    resultado = calcular_score(
        vaga=vaga,
        embedding_perfil=embedding_perfil,
        keywords_boost=[],
        keywords_penalty=[],
    )
    assert 0.0 <= resultado.score <= 1.0


def test_motivo_match_bullets():
    """Motivo do match deve ter ao menos 1 bullet."""
    vaga = _vaga("Next.js Dashboard", "painel admin com next.js typescript")
    embedding_perfil = _embedding_falso()

    resultado = calcular_score(
        vaga=vaga,
        embedding_perfil=embedding_perfil,
        keywords_boost=["next.js", "typescript"],
        keywords_penalty=[],
    )
    assert len(resultado.motivo_match["bullets"]) >= 1
    assert isinstance(resultado.motivo_match["resumo"], str)
