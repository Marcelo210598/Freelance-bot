"""
Coletor para 99Freelas (busca pública sem autenticação).
URL de busca: https://www.99freelas.com.br/projects?text=&category=ti-e-programacao
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from app.coletores.base import ColetorBase, VagaColetada

logger = logging.getLogger(__name__)

# Páginas a coletar por ciclo (baixar mais pode ser bloqueado)
MAX_PAGINAS = 3

CATEGORIAS = [
    "ti-e-programacao",
    "web-mobile-e-software",
]

URL_BASE = "https://www.99freelas.com.br/projects"


class Coletor99Freelas(ColetorBase):
    nome = "99freelas"
    intervalo_entre_requisicoes = 4.0  # gentileza com o servidor

    async def _coletar_paginas(self) -> list[VagaColetada]:
        vagas: list[VagaColetada] = []
        vistas: set[str] = set()

        for categoria in CATEGORIAS:
            for pagina in range(1, MAX_PAGINAS + 1):
                url = f"{URL_BASE}?category={categoria}&page={pagina}"
                try:
                    resposta = await self._get(url)
                    novas = self._parsear_html(resposta.text, resposta.url)
                    for v in novas:
                        if v.external_id not in vistas:
                            vistas.add(v.external_id)
                            vagas.append(v)
                    # se página vazia, parar de paginar
                    if not novas:
                        break
                except Exception as exc:
                    logger.warning("[99freelas] Erro na página %d/%s: %s", pagina, categoria, exc)
                    break

        return vagas

    def _parsear_html(self, html: str, url_base) -> list[VagaColetada]:
        """Parseia HTML da listagem de projetos do 99Freelas."""
        soup = BeautifulSoup(html, "lxml")
        vagas: list[VagaColetada] = []

        # seletor dos cards de projeto (2024–2025)
        cards = soup.select("li.project-item, div.project-item, article.project-item")

        if not cards:
            # fallback: tentar seletor mais genérico
            cards = soup.select("[class*='project']")
            logger.debug("[99freelas] Fallback de seletor, encontrados: %d", len(cards))

        for card in cards:
            try:
                # título e link
                link_tag = card.select_one("a[href*='/project/'], h2 a, h3 a, .project-title a")
                if not link_tag:
                    continue

                href = str(link_tag.get("href", ""))
                titulo = link_tag.get_text(strip=True)

                if not href or not titulo:
                    continue

                # URL absoluta
                url_vaga = href if href.startswith("http") else f"https://www.99freelas.com.br{href}"

                # ID externo: extrair do slug
                external_id = self._extrair_id(href)

                # orçamento
                orcamento_tag = card.select_one(
                    ".budget, .project-budget, [class*='budget'], [class*='valor']"
                )
                orcamento_raw = orcamento_tag.get_text(strip=True) if orcamento_tag else ""

                # descrição curta
                desc_tag = card.select_one(".description, .project-description, p")
                descricao = desc_tag.get_text(strip=True) if desc_tag else ""

                # tags/habilidades
                tags = [
                    t.get_text(strip=True)
                    for t in card.select(".skill, .tag, [class*='skill'], [class*='tag']")
                ]

                vagas.append(
                    VagaColetada(
                        fonte="99freelas",
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
                logger.debug("[99freelas] Erro ao parsear card: %s", exc)

        return vagas

    @staticmethod
    def _extrair_id(href: str) -> str:
        """Extrai ID numérico ou slug da URL."""
        match = re.search(r"/project/(\d+)", href)
        if match:
            return match.group(1)
        # usa hash do href como fallback
        import hashlib
        return hashlib.md5(href.encode()).hexdigest()[:16]
