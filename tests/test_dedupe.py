"""
Testa a lógica de deduplicação de vagas.
"""

from datetime import datetime, timezone

import pytest

from app.coletores.base import VagaColetada


def _criar_vaga(fonte: str, eid: str, titulo: str = "Teste") -> VagaColetada:
    return VagaColetada(
        fonte=fonte,
        external_id=eid,
        url=f"https://exemplo.com/{eid}",
        titulo=titulo,
        publicado_em=datetime.now(timezone.utc),
    )


def test_chave_deduplicacao_unica():
    v1 = _criar_vaga("99freelas", "123")
    v2 = _criar_vaga("workana", "123")  # mesmo ID, fonte diferente → chave diferente
    assert v1.chave_deduplicacao() != v2.chave_deduplicacao()


def test_chave_deduplicacao_identica():
    v1 = _criar_vaga("99freelas", "456")
    v2 = _criar_vaga("99freelas", "456")  # exatamente a mesma
    assert v1.chave_deduplicacao() == v2.chave_deduplicacao()


def test_deduplicacao_em_lista():
    vagas = [
        _criar_vaga("99freelas", "1", "Projeto A"),
        _criar_vaga("99freelas", "2", "Projeto B"),
        _criar_vaga("99freelas", "1", "Projeto A duplicado"),  # duplicata
        _criar_vaga("workana", "1", "Projeto A Workana"),     # mesma id, fonte diferente
    ]

    # simula a lógica de deduplicação do ciclo
    vistas: set[str] = set()
    unicas: list[VagaColetada] = []
    for v in vagas:
        chave = f"{v.fonte}:{v.external_id}"
        if chave not in vistas:
            vistas.add(chave)
            unicas.append(v)

    assert len(unicas) == 3, f"Esperava 3 vagas únicas, obteve {len(unicas)}"
    titulos = [v.titulo for v in unicas]
    assert "Projeto A duplicado" not in titulos


def test_vagas_sem_external_id():
    """Vagas sem external_id não devem causar erro."""
    v = VagaColetada(
        fonte="99freelas",
        external_id="",
        url="https://exemplo.com/test",
        titulo="Vaga sem ID",
    )
    # chave deve funcionar mesmo com string vazia
    chave = v.chave_deduplicacao()
    assert isinstance(chave, str)
    assert len(chave) > 0
