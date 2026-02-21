"""
Constrói o perfil do usuário a partir do GitHub + override opcional.
Verifica se houve mudança via `pushed_at` antes de reconstruir.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import httpx

from app.core.config import obter_config

logger = logging.getLogger(__name__)

ARQUIVO_OVERRIDE = Path("profile_override.json")
GITHUB_API = "https://api.github.com"


class ConstrutorPerfil:
    """Consolida GitHub + override em texto combinado para embeddings."""

    def __init__(self) -> None:
        self._cfg = obter_config()

    async def obter_texto_github(self) -> str:
        """Busca repositórios e bio do usuário no GitHub."""
        usuario = self._cfg.github_username
        headers = {"Accept": "application/vnd.github+json"}
        if self._cfg.github_token:
            headers["Authorization"] = f"Bearer {self._cfg.github_token}"

        async with httpx.AsyncClient(headers=headers, timeout=20.0) as cliente:
            # perfil do usuário
            try:
                resp_user = await cliente.get(f"{GITHUB_API}/users/{usuario}")
                resp_user.raise_for_status()
                dados_user = resp_user.json()
            except Exception as exc:
                logger.warning("[perfil] Erro ao buscar dados do GitHub: %s", exc)
                dados_user = {}

            # repositórios públicos (ordena por atualização)
            try:
                resp_repos = await cliente.get(
                    f"{GITHUB_API}/users/{usuario}/repos",
                    params={"sort": "updated", "per_page": 30, "type": "owner"},
                )
                resp_repos.raise_for_status()
                repos = resp_repos.json()
            except Exception as exc:
                logger.warning("[perfil] Erro ao buscar repos: %s", exc)
                repos = []

        partes = []

        # bio
        bio = dados_user.get("bio") or ""
        if bio:
            partes.append(f"Bio: {bio}")

        # nome e localização
        nome = dados_user.get("name") or usuario
        partes.append(f"Desenvolvedor: {nome}")
        if dados_user.get("location"):
            partes.append(f"Localização: {dados_user['location']}")

        # resumo dos repositórios
        for repo in repos:
            if repo.get("fork"):
                continue  # ignora forks
            linha = f"Projeto: {repo['name']}"
            if repo.get("description"):
                linha += f" — {repo['description']}"
            if repo.get("language"):
                linha += f" [{repo['language']}]"
            topics = repo.get("topics", [])
            if topics:
                linha += f" | tópicos: {', '.join(topics)}"
            partes.append(linha)

        return "\n".join(partes)

    async def checar_mudanca_github(self, ultima_atualizacao: str) -> bool:
        """
        Retorna True se o perfil do GitHub mudou desde `ultima_atualizacao`.
        Usa o campo `pushed_at` do evento mais recente de push.
        """
        usuario = self._cfg.github_username
        headers = {"Accept": "application/vnd.github+json"}
        if self._cfg.github_token:
            headers["Authorization"] = f"Bearer {self._cfg.github_token}"

        try:
            async with httpx.AsyncClient(headers=headers, timeout=10.0) as cliente:
                resp = await cliente.get(
                    f"{GITHUB_API}/users/{usuario}/events/public",
                    params={"per_page": 5},
                )
                resp.raise_for_status()
                eventos = resp.json()

            for evento in eventos:
                if evento.get("type") == "PushEvent":
                    created = evento.get("created_at", "")
                    if created > ultima_atualizacao:
                        logger.info("[perfil] Mudança detectada no GitHub: %s", created)
                        return True
            return False
        except Exception as exc:
            logger.warning("[perfil] Erro ao checar mudança GitHub: %s", exc)
            return False  # se falhar, assume que não mudou

    async def obter_texto_override(self) -> str:
        """
        Carrega perfil curado de:
        1. URL pública do site (PROFILE_URL)
        2. arquivo local profile_override.json
        """
        url_perfil = self._cfg.profile_url
        if url_perfil:
            try:
                async with httpx.AsyncClient(timeout=10.0) as cliente:
                    resp = await cliente.get(url_perfil)
                    resp.raise_for_status()
                    dados = resp.json()
                    return self._json_perfil_para_texto(dados)
            except Exception as exc:
                logger.warning("[perfil] Erro ao buscar PROFILE_URL: %s. Tentando arquivo local.", exc)

        # fallback: arquivo local
        if ARQUIVO_OVERRIDE.exists():
            try:
                dados = json.loads(ARQUIVO_OVERRIDE.read_text(encoding="utf-8"))
                return self._json_perfil_para_texto(dados)
            except Exception as exc:
                logger.warning("[perfil] Erro ao ler profile_override.json: %s", exc)

        return ""

    @staticmethod
    def _json_perfil_para_texto(dados: dict) -> str:
        """Converte JSON de perfil curado em texto para embeddings."""
        partes = []
        if dados.get("resumo"):
            partes.append(f"Resumo profissional: {dados['resumo']}")
        for skill in dados.get("habilidades", []):
            partes.append(f"Habilidade: {skill}")
        for projeto in dados.get("projetos_destaque", []):
            partes.append(f"Projeto destaque: {projeto}")
        if dados.get("areas"):
            partes.append(f"Áreas de atuação: {', '.join(dados['areas'])}")
        return "\n".join(partes)

    async def construir_perfil_completo(self) -> str:
        """Retorna texto combinado GitHub + override."""
        texto_github = await self.obter_texto_github()
        texto_override = await self.obter_texto_override()

        partes = []
        if texto_github:
            partes.append(f"=== GitHub ===\n{texto_github}")
        if texto_override:
            partes.append(f"=== Perfil Curado ===\n{texto_override}")

        combinado = "\n\n".join(partes)
        logger.info("[perfil] Texto combinado gerado: %d caracteres", len(combinado))
        return combinado
