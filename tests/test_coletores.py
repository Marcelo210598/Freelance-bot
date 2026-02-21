"""
Testes de parsing dos coletores usando fixtures HTML/JSON locais.
Não fazem requisições HTTP reais.
"""

import json
from pathlib import Path

import pytest

from app.coletores.freelancer import ColetorFreelancer
from app.coletores.noventa_freelas import Coletor99Freelas
from app.coletores.workana import ColetorWorkana

FIXTURES = Path(__file__).parent / "fixtures"


# ── 99Freelas ─────────────────────────────────────────────────────────────────
def test_99freelas_parsear_html():
    html = (FIXTURES / "99freelas.html").read_text(encoding="utf-8")
    coletor = Coletor99Freelas()
    vagas = coletor._parsear_html(html, "https://www.99freelas.com.br")

    assert len(vagas) >= 3, f"Esperava ao menos 3 vagas, obteve {len(vagas)}"

    # verifica estrutura da primeira vaga
    v = vagas[0]
    assert v.fonte == "99freelas"
    assert v.external_id, "external_id deve ser preenchido"
    assert v.url.startswith("http"), f"URL inválida: {v.url}"
    assert len(v.titulo) > 5, "Título muito curto"


def test_99freelas_sem_duplicatas():
    html = (FIXTURES / "99freelas.html").read_text(encoding="utf-8")
    coletor = Coletor99Freelas()
    vagas = coletor._parsear_html(html, "https://www.99freelas.com.br")
    ids = [v.external_id for v in vagas]
    assert len(ids) == len(set(ids)), "Vagas duplicadas no parsing"


# ── Workana ───────────────────────────────────────────────────────────────────
def test_workana_parsear_html():
    html = (FIXTURES / "workana.html").read_text(encoding="utf-8")
    coletor = ColetorWorkana()
    vagas = coletor._parsear_html(html)

    assert len(vagas) >= 2, f"Esperava ao menos 2 vagas, obteve {len(vagas)}"
    for v in vagas:
        assert v.fonte == "workana"
        assert v.url.startswith("http")


def test_workana_extrai_orcamento():
    html = (FIXTURES / "workana.html").read_text(encoding="utf-8")
    coletor = ColetorWorkana()
    vagas = coletor._parsear_html(html)
    # pelo menos uma vaga deve ter orçamento preenchido
    com_orcamento = [v for v in vagas if v.orcamento_raw]
    assert len(com_orcamento) >= 1, "Nenhuma vaga com orçamento parseado"


# ── Freelancer ────────────────────────────────────────────────────────────────
def test_freelancer_parsear_json():
    dados = json.loads((FIXTURES / "freelancer.json").read_text(encoding="utf-8"))
    coletor = ColetorFreelancer()
    vagas = coletor._parsear_json(dados)

    assert len(vagas) == 3, f"Esperava 3 vagas, obteve {len(vagas)}"
    assert vagas[0].fonte == "freelancer"
    assert vagas[0].external_id == "99001"
    assert "FastAPI" in vagas[0].titulo or "fastapi" in vagas[0].descricao.lower()


def test_freelancer_orcamento_formatado():
    dados = json.loads((FIXTURES / "freelancer.json").read_text(encoding="utf-8"))
    coletor = ColetorFreelancer()
    vagas = coletor._parsear_json(dados)
    v = vagas[0]
    assert "R$" in v.orcamento_raw or v.orcamento_raw != "", "Orçamento não formatado"


def test_freelancer_tags():
    dados = json.loads((FIXTURES / "freelancer.json").read_text(encoding="utf-8"))
    coletor = ColetorFreelancer()
    vagas = coletor._parsear_json(dados)
    assert len(vagas[0].tags) >= 2, "Tags não parseadas"
