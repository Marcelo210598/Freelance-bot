"""
Configurações centralizadas via variáveis de ambiente.
Usa pydantic-settings para validação e defaults sensatos.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracoes(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Banco de dados ────────────────────────────────────
    database_url: str

    # ── Segurança ─────────────────────────────────────────
    admin_token: str

    # ── Telegram ──────────────────────────────────────────
    telegram_bot_token: str
    telegram_chat_id: str

    # ── GitHub ────────────────────────────────────────────
    github_username: str
    github_token: str = ""

    # ── Perfil curado (opcional) ──────────────────────────
    profile_url: str = ""

    # ── Defaults de configuração (sobrepostos pelo dashboard) ─
    diaria_base: float = 100.0
    threshold_score: float = 0.45
    freq_minutos: int = 45
    github_refresh_horas: int = 8

    # ── Ambiente ──────────────────────────────────────────
    env: str = "development"
    log_level: str = "INFO"


@lru_cache
def obter_config() -> Configuracoes:
    """Singleton — instanciado uma vez e reutilizado."""
    return Configuracoes()  # type: ignore[call-arg]
