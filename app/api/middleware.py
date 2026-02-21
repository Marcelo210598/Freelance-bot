"""
Middleware de autenticação via header X-ADMIN-TOKEN.
"""

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import obter_config

_header_token = APIKeyHeader(name="X-ADMIN-TOKEN", auto_error=False)


async def verificar_token(token: str | None = Security(_header_token)) -> str:
    """Dependência do FastAPI. Rejeita requisições sem token válido."""
    cfg = obter_config()
    if not token or token != cfg.admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou ausente. Informe X-ADMIN-TOKEN.",
        )
    return token
