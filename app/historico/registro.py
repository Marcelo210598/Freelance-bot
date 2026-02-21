"""
Registro de execuções em arquivo (history/YYYY-MM-DD/run_XX.json + .log).
Garante que o histórico de desenvolvimento (DEVLOG.md) exista.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PASTA_HISTORY = Path("history")


def _pasta_hoje() -> Path:
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    pasta = PASTA_HISTORY / hoje
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def _proximo_numero_run(pasta: Path) -> int:
    """Determina o número sequencial do próximo run do dia."""
    existentes = list(pasta.glob("run_*.json"))
    if not existentes:
        return 1
    numeros = []
    for f in existentes:
        try:
            n = int(f.stem.split("_")[1])
            numeros.append(n)
        except (IndexError, ValueError):
            pass
    return (max(numeros) + 1) if numeros else 1


class RegistradorExecucao:
    """Salva dados de uma execução em JSON e log."""

    def __init__(self) -> None:
        self._pasta = _pasta_hoje()
        self._numero = _proximo_numero_run(self._pasta)
        self._caminho_json = self._pasta / f"run_{self._numero:03d}.json"
        self._caminho_log = self._pasta / f"run_{self._numero:03d}.log"
        self._log_linhas: list[str] = []

    @property
    def caminho(self) -> str:
        return str(self._caminho_json)

    def registrar_log(self, mensagem: str, nivel: str = "INFO") -> None:
        """Adiciona linha ao log da execução."""
        ts = datetime.now(timezone.utc).isoformat()
        linha = f"[{ts}] [{nivel}] {mensagem}"
        self._log_linhas.append(linha)
        # espelha no logger padrão
        getattr(logger, nivel.lower(), logger.info)(mensagem)

    def salvar(self, dados: dict[str, Any]) -> str:
        """Salva JSON da execução e o log. Retorna caminho do JSON."""
        dados["_meta"] = {
            "run": self._numero,
            "data": datetime.now(timezone.utc).isoformat(),
            "arquivo_log": str(self._caminho_log),
        }
        try:
            self._caminho_json.write_text(
                json.dumps(dados, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
            self._caminho_log.write_text(
                "\n".join(self._log_linhas),
                encoding="utf-8",
            )
            logger.info("[historico] Run %03d salvo em %s", self._numero, self._caminho_json)
        except Exception as exc:
            logger.error("[historico] Erro ao salvar run: %s", exc)
        return str(self._caminho_json)


def garantir_devlog() -> None:
    """Cria o DEVLOG.md inicial se não existir."""
    PASTA_HISTORY.mkdir(exist_ok=True)
    devlog = PASTA_HISTORY / "DEVLOG.md"
    if not devlog.exists():
        devlog.write_text(
            "# DEVLOG — Freelance-bot\n\n"
            "Registro de desenvolvimento e execuções.\n\n"
            "---\n\n"
            "## 2026-02-21 — Setup inicial\n\n"
            "### O que foi implementado\n"
            "- Estrutura completa do projeto criada\n"
            "- Modelos de banco de dados (SQLAlchemy + Alembic)\n"
            "- API FastAPI com autenticação X-ADMIN-TOKEN\n"
            "- Worker com APScheduler\n"
            "- Coletores: 99Freelas, Workana, Freelancer.com\n"
            "- Embeddings locais (sentence-transformers)\n"
            "- Scoring + estimativa de valor/prazo\n"
            "- Telegram notifier\n"
            "- Dashboard Next.js (/admin)\n\n"
            "### Pendências\n"
            "- [ ] Configurar .env com credenciais reais\n"
            "- [ ] Rodar `alembic upgrade head` para criar tabelas\n"
            "- [ ] Deploy no Railway (API + Worker)\n"
            "- [ ] Integrar dashboard no site Vercel\n\n"
            "### Próxima ação sugerida\n"
            "1. `cp .env.example .env` e preencher variáveis\n"
            "2. `pip install -r requirements.txt`\n"
            "3. `alembic upgrade head`\n"
            "4. `uvicorn app.api.main:app --reload` para testar API\n"
            "5. `python -m app.worker.main` para testar worker\n\n"
            "### Comandos úteis\n"
            "```bash\n"
            "# Rodar localmente\n"
            "uvicorn app.api.main:app --reload --port 8000\n"
            "python -m app.worker.main\n\n"
            "# Migrações\n"
            "alembic upgrade head\n"
            "alembic revision --autogenerate -m 'descricao'\n\n"
            "# Testes\n"
            "pytest tests/ -v\n"
            "```\n",
            encoding="utf-8",
        )


def atualizar_devlog(entrada: str) -> None:
    """Acrescenta entrada ao DEVLOG.md."""
    garantir_devlog()
    devlog = PASTA_HISTORY / "DEVLOG.md"
    conteudo = devlog.read_text(encoding="utf-8")
    devlog.write_text(conteudo + "\n\n---\n\n" + entrada, encoding="utf-8")
