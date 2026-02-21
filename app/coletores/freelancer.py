"""
Coletor para Freelancer.com — usa a API pública de busca de projetos.
Endpoint público: https://www.freelancer.com/api/projects/0.1/projects/active/
Não requer autenticação para listagem básica.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.coletores.base import ColetorBase, VagaColetada

logger = logging.getLogger(__name__)

# Categorias de TI no Freelancer (IDs da API pública)
# 3 = Web Development, 2 = Software Development, 7 = Mobile Phones
CATEGORIAS_ID = [3, 2, 7]
MAX_RESULTADOS = 20
URL_API = "https://www.freelancer.com/api/projects/0.1/projects/active/"


class ColetorFreelancer(ColetorBase):
    nome = "freelancer"
    intervalo_entre_requisicoes = 6.0

    async def _coletar_paginas(self) -> list[VagaColetada]:
        vagas: list[VagaColetada] = []
        vistas: set[str] = set()

        for cat_id in CATEGORIAS_ID:
            params = {
                "job_details": "true",
                "full_description": "false",
                "compact": "true",
                "limit": MAX_RESULTADOS,
                "languages[]": "pt",
                "jobs[]": cat_id,
                "sort_field": "time_updated",
                "reverse_sort": "false",
            }
            try:
                resposta = await self._get(URL_API, params=params)
                novas = self._parsear_json(resposta.json())
                for v in novas:
                    if v.external_id not in vistas:
                        vistas.add(v.external_id)
                        vagas.append(v)
            except Exception as exc:
                logger.warning("[freelancer] Erro categoria %d: %s", cat_id, exc)
                # fallback: busca por HTML da landing page
                vagas.extend(await self._fallback_html(cat_id))

        return vagas

    def _parsear_json(self, dados: dict) -> list[VagaColetada]:
        """Parseia resposta da API pública do Freelancer."""
        vagas: list[VagaColetada] = []
        projetos = dados.get("result", {}).get("projects", [])

        for p in projetos:
            try:
                pid = str(p.get("id", ""))
                if not pid:
                    continue

                titulo = p.get("title", "").strip()
                if not titulo:
                    continue

                url_vaga = f"https://www.freelancer.com/projects/{p.get('seo_url', pid)}"

                # orçamento
                budget = p.get("budget", {})
                min_b = budget.get("minimum", "")
                max_b = budget.get("maximum", "")
                moeda = budget.get("currency", {}).get("sign", "")
                orcamento_raw = f"{moeda}{min_b} - {moeda}{max_b}" if min_b else ""

                # data de publicação
                publicado_ts = p.get("time_submitted") or p.get("time_updated")
                publicado_em = (
                    datetime.fromtimestamp(publicado_ts, tz=timezone.utc)
                    if publicado_ts
                    else datetime.now(timezone.utc)
                )

                # habilidades
                skills = p.get("jobs", []) or []
                tags = [s.get("name", "") for s in skills if s.get("name")]

                descricao = p.get("preview_description", "") or p.get("description", "") or ""

                vagas.append(
                    VagaColetada(
                        fonte="freelancer",
                        external_id=pid,
                        url=url_vaga,
                        titulo=titulo,
                        descricao=descricao[:2000],
                        orcamento_raw=orcamento_raw,
                        publicado_em=publicado_em,
                        tags=tags[:10],
                        raw_json={"id": pid, "currency": moeda},
                    )
                )
            except Exception as exc:
                logger.debug("[freelancer] Erro ao parsear projeto: %s", exc)

        return vagas

    async def _fallback_html(self, categoria_id: int) -> list[VagaColetada]:
        """
        Fallback: tenta coletar via HTML da página de projetos.
        Registra no log se usado.
        """
        logger.info("[freelancer] Usando fallback HTML para categoria %d", categoria_id)
        try:
            from bs4 import BeautifulSoup
            url = f"https://www.freelancer.com/jobs/{categoria_id}/?language_code=pt"
            resposta = await self._get(url)
            soup = BeautifulSoup(resposta.text, "lxml")
            vagas = []

            for card in soup.select("[data-project-id], article.JobSearchCard"):
                link = card.select_one("a[href*='/projects/']")
                titulo_tag = card.select_one("a[href*='/projects/'], h2, h3")
                if not link or not titulo_tag:
                    continue

                href = str(link.get("href", ""))
                url_vaga = href if href.startswith("http") else f"https://www.freelancer.com{href}"
                pid = str(card.get("data-project-id", "")) or href.split("/")[-1]

                vagas.append(
                    VagaColetada(
                        fonte="freelancer",
                        external_id=pid or href,
                        url=url_vaga,
                        titulo=titulo_tag.get_text(strip=True),
                        raw_json={"fallback": True},
                    )
                )
            return vagas
        except Exception as exc:
            logger.warning("[freelancer] Fallback HTML também falhou: %s", exc)
            return []
