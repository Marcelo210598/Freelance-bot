"""
Envio de alertas via Telegram Bot API.
Máximo 5 mensagens por ciclo para evitar spam.
Suporta agrupamento e formatação Markdown.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from app.core.config import obter_config

logger = logging.getLogger(__name__)

MAX_ALERTAS_POR_CICLO = 5
URL_TELEGRAM = "https://api.telegram.org/bot{token}/sendMessage"


@dataclass
class DadosAlerta:
    titulo: str
    fonte: str
    url: str
    score: float
    complexity_score: int
    valor_sugerido: float
    dias_estimados: int
    motivo_bullets: list[str]
    proposta_curta: str


class NotificadorTelegram:
    def __init__(self) -> None:
        cfg = obter_config()
        self._token = cfg.telegram_bot_token
        self._chat_id = cfg.telegram_chat_id
        self._url = URL_TELEGRAM.format(token=self._token)

    async def enviar_alertas(self, alertas: list[DadosAlerta]) -> int:
        """
        Envia até MAX_ALERTAS_POR_CICLO mensagens.
        Retorna quantidade de mensagens enviadas com sucesso.
        """
        if not alertas:
            return 0

        enviados = 0
        top = alertas[:MAX_ALERTAS_POR_CICLO]

        async with httpx.AsyncClient(timeout=15.0) as cliente:
            for alerta in top:
                mensagem = self._formatar_mensagem(alerta)
                try:
                    resp = await cliente.post(
                        self._url,
                        json={
                            "chat_id": self._chat_id,
                            "text": mensagem,
                            "parse_mode": "Markdown",
                            "disable_web_page_preview": False,
                        },
                    )
                    resp.raise_for_status()
                    enviados += 1
                    logger.info("[telegram] Alerta enviado: %s", alerta.titulo[:50])
                except Exception as exc:
                    logger.warning("[telegram] Falha ao enviar alerta: %s", exc)

        if len(alertas) > MAX_ALERTAS_POR_CICLO:
            # aviso de agrupamento
            await self._enviar_resumo(cliente, len(alertas), enviados)

        return enviados

    async def _enviar_resumo(self, cliente: httpx.AsyncClient, total: int, enviados: int) -> None:
        """Avisa que existem mais vagas além das notificadas."""
        try:
            msg = (
                f"📦 *{total - enviados} vaga(s) adicionais* encontradas neste ciclo\\.\n"
                f"Acesse o painel /admin para ver todas\\."
            )
            await cliente.post(
                self._url,
                json={"chat_id": self._chat_id, "text": msg, "parse_mode": "MarkdownV2"},
            )
        except Exception:
            pass  # não crítico

    @staticmethod
    def _formatar_mensagem(alerta: DadosAlerta) -> str:
        """Formata mensagem Markdown para o Telegram."""
        fonte_emoji = {
            "99freelas": "🇧🇷",
            "workana": "🌎",
            "freelancer": "🌐",
        }.get(alerta.fonte, "📋")

        score_bar = "🟢" if alerta.score >= 0.7 else "🟡" if alerta.score >= 0.5 else "🔴"
        valor_fmt = f"R$ {alerta.valor_sugerido:,.0f}".replace(",", ".")

        bullets = "\n".join(f"  • {b}" for b in alerta.motivo_bullets[:3])

        # proposta curta: só primeiras 2 linhas
        linhas_proposta = alerta.proposta_curta.strip().split("\n")
        proposta_resumida = linhas_proposta[0] if linhas_proposta else ""

        return (
            f"{fonte_emoji} *Nova vaga — {alerta.fonte.upper()}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 *{alerta.titulo[:80]}*\n\n"
            f"{score_bar} Score: `{alerta.score:.0%}` | Complexidade: `{alerta.complexity_score}/100`\n"
            f"💰 Valor sugerido: `{valor_fmt}` | Prazo: `{alerta.dias_estimados}d`\n\n"
            f"🎯 *Por que é uma boa match?*\n{bullets}\n\n"
            f"📝 *Proposta sugerida:*\n_{proposta_resumida}_\n\n"
            f"🔗 [Ver vaga]({alerta.url})"
        )

    async def enviar_mensagem_simples(self, texto: str) -> bool:
        """Envia texto livre (para avisos do sistema)."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as cliente:
                resp = await cliente.post(
                    self._url,
                    json={"chat_id": self._chat_id, "text": texto, "parse_mode": "Markdown"},
                )
                resp.raise_for_status()
            return True
        except Exception as exc:
            logger.warning("[telegram] Erro ao enviar mensagem simples: %s", exc)
            return False
