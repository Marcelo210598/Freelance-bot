"""
Coletor para 99Freelas (busca pública sem autenticação).
URL de busca: https://www.99freelas.com.br/projects?text=&category=ti-e-programacao
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup, Tag

from app.coletores.base import ColetorBase, VagaColetada

logger = logging.getLogger(__name__)

# Páginas a coletar por ciclo (baixar mais pode ser bloqueado)
MAX_PAGINAS = 3

CATEGORIAS = [
    "ti-e-programacao",
    "web-mobile-e-software",
]

URL_BASE = "https://www.99freelas.com.br/projects"

# Classes CSS que indicam vaga bloqueada para assinantes
_CLASSES_PREMIUM = {
    "premium", "locked", "bloqueado", "subscriber", "exclusive",
    "plan-required", "assinante", "restricted", "upgrade",
}

# Textos que indicam vaga exclusiva para plano pago
_TEXTOS_PREMIUM = [
    "exclusivo para assinante",
    "somente para assinante",
    "apenas para assinante",
    "disponível para assinante",
    "disponivel para assinante",
    "acesso exclusivo",
    "plano pago",
    "upgrade",
    "assine para ver",
    "assine agora",
    "seja assinante",
    "conteúdo exclusivo",
    "conteudo exclusivo",
]


class Coletor99Freelas(ColetorBase):
    nome = "99freelas"
    intervalo_entre_requisicoes = 4.0  # gentileza com o servidor

    async def _coletar_paginas(self) -> list[VagaColetada]:
        vagas: list[VagaColetada] = []
        vistas: set[str] = set()
        total_puladas = 0

        for categoria in CATEGORIAS:
            for pagina in range(1, MAX_PAGINAS + 1):
                url = f"{URL_BASE}?category={categoria}&page={pagina}"
                try:
                    resposta = await self._get(url)
                    novas, puladas = self._parsear_html(resposta.text, resposta.url)
                    total_puladas += puladas
                    for v in novas:
                        if v.external_id not in vistas:
                            vistas.add(v.external_id)
                            vagas.append(v)
                    # se página vazia, parar de paginar
                    if not novas and puladas == 0:
                        break
                except Exception as exc:
                    logger.warning("[99freelas] Erro na página %d/%s: %s", pagina, categoria, exc)
                    break

        if total_puladas:
            logger.info("[99freelas] %d vaga(s) ignoradas por exigirem plano pago.", total_puladas)

        return vagas

    def _parsear_html(self, html: str, url_base) -> tuple[list[VagaColetada], int]:
        """
        Parseia HTML da listagem de projetos do 99Freelas.
        Retorna (vagas_livres, quantidade_puladas_por_ser_premium).
        """
        soup = BeautifulSoup(html, "lxml")
        vagas: list[VagaColetada] = []
        puladas = 0

        # seletor dos cards de projeto (2024–2025)
        cards = soup.select("li.project-item, div.project-item, article.project-item")

        if not cards:
            # fallback: tentar seletor mais genérico
            cards = soup.select("[class*='project']")
            logger.debug("[99freelas] Fallback de seletor, encontrados: %d", len(cards))

        for card in cards:
            try:
                # ── detectar vaga premium/bloqueada ──────────────────────────
                if self._e_vaga_premium(card):
                    puladas += 1
                    logger.debug("[99freelas] Vaga premium ignorada: %s", card.get_text(separator=" ", strip=True)[:80])
                    continue

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

        return vagas, puladas

    @staticmethod
    def _e_vaga_premium(card: Tag) -> bool:
        """
        Retorna True se o card de vaga exige plano pago (não acessível no free).

        Detecta por:
        - Classes CSS conhecidas (premium, locked, bloqueado, etc.)
        - Textos indicando restrição de assinante
        - Ícone de cadeado (SVG path ou classe fa-lock / icon-lock)
        - Atributos data- indicando restrição
        """
        # 1. classes CSS do card e filhos indicando premium
        todas_classes: set[str] = set()
        for el in card.find_all(True):
            for cls in el.get("class", []):
                todas_classes.add(cls.lower())

        if todas_classes & _CLASSES_PREMIUM:
            return True

        # 2. atributos data- sugerindo restrição
        for el in card.find_all(True):
            for attr, val in el.attrs.items():
                if "premium" in attr.lower() or "locked" in attr.lower() or "subscriber" in attr.lower():
                    return True
                if isinstance(val, str) and any(k in val.lower() for k in ("premium", "locked", "subscriber")):
                    return True

        # 3. ícone de cadeado (Font Awesome ou similar)
        lock_icons = card.select(
            "i.fa-lock, i.fa-unlock-alt, span.icon-lock, "
            "[class*='lock'], [class*='cadeado']"
        )
        if lock_icons:
            return True

        # 4. SVG com path de cadeado (viewBox ou path típico de lock)
        for svg in card.find_all("svg"):
            svg_text = str(svg).lower()
            if "lock" in svg_text or "cadeado" in svg_text:
                return True

        # 5. texto do card contém frase de restrição
        texto_card = card.get_text(separator=" ", strip=True).lower()
        if any(frase in texto_card for frase in _TEXTOS_PREMIUM):
            return True

        return False

    @staticmethod
    def _extrair_id(href: str) -> str:
        """Extrai ID numérico ou slug da URL."""
        match = re.search(r"/project/(\d+)", href)
        if match:
            return match.group(1)
        # usa hash do href como fallback
        import hashlib
        return hashlib.md5(href.encode()).hexdigest()[:16]
