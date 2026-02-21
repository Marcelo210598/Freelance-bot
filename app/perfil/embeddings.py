"""
Geração e armazenamento de embeddings usando Sentence Transformers.
Modelo: all-MiniLM-L6-v2 (leve, rápido, 384 dimensões, sem custo de API).
Embeddings armazenados no DB como numpy array em base64.
"""

from __future__ import annotations

import base64
import logging
from functools import lru_cache

import numpy as np

logger = logging.getLogger(__name__)

MODELO_NOME = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _carregar_modelo():
    """Carrega o modelo uma única vez (singleton)."""
    logger.info("[embeddings] Carregando modelo %s...", MODELO_NOME)
    from sentence_transformers import SentenceTransformer
    modelo = SentenceTransformer(MODELO_NOME)
    logger.info("[embeddings] Modelo carregado.")
    return modelo


def gerar_embedding(texto: str) -> np.ndarray:
    """Gera embedding para um texto. Retorna array float32 de 384 dims."""
    modelo = _carregar_modelo()
    embedding = modelo.encode(texto, normalize_embeddings=True)
    return embedding.astype(np.float32)


def serializar_embedding(embedding: np.ndarray) -> str:
    """Converte numpy array para string base64 (armazenável no DB)."""
    return base64.b64encode(embedding.tobytes()).decode("utf-8")


def deserializar_embedding(b64: str) -> np.ndarray:
    """Converte string base64 de volta para numpy array."""
    dados = base64.b64decode(b64)
    return np.frombuffer(dados, dtype=np.float32)


def similaridade_cosseno(a: np.ndarray, b: np.ndarray) -> float:
    """
    Cosine similarity entre dois vetores.
    Como usamos normalize_embeddings=True, é só o produto escalar.
    Retorna valor entre -1 e 1 (na prática 0 a 1 para textos).
    """
    norma_a = np.linalg.norm(a)
    norma_b = np.linalg.norm(b)
    if norma_a == 0 or norma_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norma_a * norma_b))


def gerar_embeddings_lote(textos: list[str], batch_size: int = 32) -> list[np.ndarray]:
    """Gera embeddings para uma lista de textos de forma eficiente."""
    modelo = _carregar_modelo()
    embeddings = modelo.encode(
        textos,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=len(textos) > 10,
    )
    return [e.astype(np.float32) for e in embeddings]
