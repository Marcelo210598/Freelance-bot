"""
Coletor para Workana (busca pública de projetos).
URL: https://www.workana.com/jobs?category=it-programming&language=pt
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from app.coletores.base import ColetorBase, VagaColetada

logger = logging.getLogger(__name__)

MAX_PAGINAS = 3
URL_BASE = "https://www.workana.com/jobs"
PARAMETROS_PADRAO = "category=it-programming&language=pt"


class ColetorWorkana(ColetorBase):
    nome = "workana"
    intervalo_entre_requisicoes = 5.0

    async def _coletar_paginas(self) -> list[VagaColetada]:
        vagas: list[VagaColetada] = []
        vistas: set[str] = set()

        for pagina in range(1, MAX_PAGINAS + 1):
            url = f"{URL_BASE}?{PARAMETROS_PADRAO}&page={pagina}"
            try:
                resposta = await self._get(url)
                novas = self._parsear_html(resposta.text)
                if not novas:
                    break
                for v in novas:
                    if v.external_id not in vistas:
                        vistas.add(v.external_id)
                        vagas.append(v)
            except Exception as exc:
                logger.warning("[workana] Erro na página %d: %s", pagina, exc)
                break

        return vagas

    def _parsear_html(self, html: str) -> list[VagaColetada]:
        soup = BeautifulSoup(html, "lxml")
        vagas: list[VagaColetada] = []

        # Workana usa divs com classe que contém "project"
        cards = soup.select(
            "div.project, article.project, li.project, "
            "[class*='project-item'], [class*='job-item']"
        )

        if not cards:
            # fallback: blocos com link de projeto
            cards = soup.select("div:has(a[href*='/job/'])")
            logger.debug("[workana] Fallback de seletor, encontrados: %d", len(cards))

        for card in cards:
            try:
                link_tag = card.select_one("a[href*='/job/'], h2 a, h3 a, .project-title a")
                if not link_tag:
                    continue

                href = str(link_tag.get("href", ""))
                titulo = link_tag.get_text(strip=True)

                if not href or not titulo:
                    continue

                url_vaga = href if href.startswith("http") else f"https://www.workana.com{href}"
                external_id = self._extrair_id(href)

                # orçamento
                budget_tag = card.select_one(
                    ".budget, .project-budget, [class*='budget'], [class*='price']"
                )
                orcamento_raw = budget_tag.get_text(strip=True) if budget_tag else ""

                # descrição
                desc_tag = card.select_one(".project-description, .description, p.description")
                descricao = desc_tag.get_text(strip=True) if desc_tag else ""

                # habilidades
                tags = [
                    t.get_text(strip=True)
                    for t in card.select(".skill, .tag, span.label, [class*='skill']")
                ]

                vagas.append(
                    VagaColetada(
                        fonte="workana",
                        external_id=external_id,
                        url=url_vaga,
                        titulo=titulo,
                        descricao=descricao,
                        orcamento_raw=orcamento_raw,
                        publicado_em=datetime.now(timezone.utc),
                        tags=tags[:10],
                        raw_json={"href": href},
                    )
                )
            except Exception as exc:
                logger.debug("[workana] Erro ao parsear card: %s", exc)

        return vagas

    @staticmethod
    def _extrair_id(href: str) -> str:
        match = re.search(r"/job/([^/?#]+)", href)
        if match:
            return match.group(1)
        import hashlib
        return hashlib.md5(href.encode()).hexdigest()[:16]
