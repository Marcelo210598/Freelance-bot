"""
Entry-point da API FastAPI (Railway — serviço 1).
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import jobs, runs, settings, stats
from app.core.config import obter_config

cfg = obter_config()

logging.basicConfig(
    level=cfg.log_level,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Freelance-bot API",
    description="API interna para o sistema de rastreamento de vagas freelance.",
    version="1.0.0",
    docs_url="/docs" if cfg.env == "development" else None,  # sem docs em produção
    redoc_url=None,
)

# CORS: só permite o domínio do Vercel (e localhost para dev)
origens_permitidas = [
    "http://localhost:3000",
    "https://localhost:3000",
]
if cfg.env == "production":
    # adicionar domínio Vercel via env se necessário
    import os
    vercel_url = os.getenv("VERCEL_URL", "")
    if vercel_url:
        origens_permitidas.append(f"https://{vercel_url}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origens_permitidas,
    allow_credentials=True,
    allow_methods=["GET", "PATCH"],
    allow_headers=["X-ADMIN-TOKEN", "Content-Type"],
)

# registra os roteadores
app.include_router(stats.roteador)
app.include_router(jobs.roteador)
app.include_router(settings.roteador)
app.include_router(runs.roteador)


@app.get("/health")
async def health_check() -> dict:
    """Endpoint de saúde usado pelo Railway para verificar o serviço."""
    return {"status": "ok", "servico": "freelance-bot-api"}


logger.info("API iniciada. Ambiente: %s", cfg.env)
