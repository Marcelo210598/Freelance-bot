"""
Modelos SQLAlchemy (tabelas do banco de dados).

Tabelas:
  - vagas          → jobs coletados de todas as fontes
  - pontuacoes     → score de match + estimativa de valor/prazo
  - candidaturas   → controle manual de status
  - perfil         → perfil do usuário (GitHub + override)
  - configuracoes  → configurações do sistema (linha única, id=1)
  - execucoes      → histórico de ciclos do worker
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ─────────────────────────────────────────────────────────────────────────────
# Enum de status das candidaturas
# ─────────────────────────────────────────────────────────────────────────────
class StatusCandidatura(str, enum.Enum):
    encontrado = "encontrado"
    candidatei = "candidatei"
    em_conversa = "em_conversa"
    aceita = "aceita"
    recusada = "recusada"
    concluida = "concluida"


# ─────────────────────────────────────────────────────────────────────────────
# vagas
# ─────────────────────────────────────────────────────────────────────────────
class Vaga(Base):
    __tablename__ = "vagas"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fonte: Mapped[str] = mapped_column(String(50), nullable=False)          # 99freelas | workana | freelancer
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)   # ID original da plataforma
    url: Mapped[str] = mapped_column(Text, nullable=False)
    titulo: Mapped[str] = mapped_column(Text, nullable=False)
    descricao: Mapped[str] = mapped_column(Text, default="")
    orcamento_raw: Mapped[str] = mapped_column(String(255), default="")     # texto original (ex: "R$ 500 - 800")
    publicado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    raw_json: Mapped[dict] = mapped_column(JSON, default=dict)              # dados brutos da fonte
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # relacionamentos
    pontuacao: Mapped[PontuacaoVaga | None] = relationship(
        "PontuacaoVaga", back_populates="vaga", uselist=False, cascade="all, delete-orphan"
    )
    candidatura: Mapped[Candidatura | None] = relationship(
        "Candidatura", back_populates="vaga", uselist=False, cascade="all, delete-orphan"
    )


# ─────────────────────────────────────────────────────────────────────────────
# pontuacoes
# ─────────────────────────────────────────────────────────────────────────────
class PontuacaoVaga(Base):
    __tablename__ = "pontuacoes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    vaga_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("vagas.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    score: Mapped[float] = mapped_column(Float, default=0.0)               # score final (0–1)
    similaridade: Mapped[float] = mapped_column(Float, default=0.0)        # cosine similarity dos embeddings
    score_palavras: Mapped[float] = mapped_column(Float, default=0.0)      # boost/penalty por keywords
    complexity_score: Mapped[int] = mapped_column(Integer, default=0)      # 0–100
    dias_estimados: Mapped[int] = mapped_column(Integer, default=1)
    valor_sugerido: Mapped[float] = mapped_column(Float, default=0.0)
    motivo_match: Mapped[dict] = mapped_column(JSON, default=dict)          # {"bullets": [...], "resumo": "..."}
    proposta_sugerida: Mapped[str] = mapped_column(Text, default="")
    calculado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    vaga: Mapped[Vaga] = relationship("Vaga", back_populates="pontuacao")


# ─────────────────────────────────────────────────────────────────────────────
# candidaturas
# ─────────────────────────────────────────────────────────────────────────────
class Candidatura(Base):
    __tablename__ = "candidaturas"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    vaga_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("vagas.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    status: Mapped[StatusCandidatura] = mapped_column(
        Enum(StatusCandidatura), default=StatusCandidatura.encontrado
    )
    valor_final: Mapped[float | None] = mapped_column(Float, nullable=True)
    prazo_final: Mapped[int | None] = mapped_column(Integer, nullable=True)  # dias
    notas: Mapped[str] = mapped_column(Text, default="")
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    vaga: Mapped[Vaga] = relationship("Vaga", back_populates="candidatura")


# ─────────────────────────────────────────────────────────────────────────────
# perfil (linha única — id = 1)
# ─────────────────────────────────────────────────────────────────────────────
class Perfil(Base):
    __tablename__ = "perfil"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    github_texto: Mapped[str] = mapped_column(Text, default="")
    override_texto: Mapped[str] = mapped_column(Text, default="")
    texto_combinado: Mapped[str] = mapped_column(Text, default="")
    embedding_b64: Mapped[str] = mapped_column(Text, default="")           # numpy array em base64
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ─────────────────────────────────────────────────────────────────────────────
# configuracoes (linha única — id = 1)
# ─────────────────────────────────────────────────────────────────────────────
class Configuracao(Base):
    __tablename__ = "configuracoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    diaria_base: Mapped[float] = mapped_column(Float, default=100.0)
    threshold_score: Mapped[float] = mapped_column(Float, default=0.45)
    freq_minutos: Mapped[int] = mapped_column(Integer, default=45)
    github_refresh_horas: Mapped[int] = mapped_column(Integer, default=8)
    # JSON com listas de palavras-chave
    keywords_boost: Mapped[list] = mapped_column(
        JSON,
        default=lambda: [
            "next.js", "fastapi", "python", "typescript", "react",
            "postgres", "api", "fullstack", "node", "docker",
        ],
    )
    keywords_penalty: Mapped[list] = mapped_column(
        JSON,
        default=lambda: ["wordpress", "php", "magento", "wix", "drupal"],
    )
    # pisos mínimos de valor por categoria (R$)
    pisos_por_categoria: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "simples": 150.0,
            "medio": 400.0,
            "complexo": 900.0,
            "muito_complexo": 1800.0,
        },
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ─────────────────────────────────────────────────────────────────────────────
# execucoes (histórico de ciclos do worker)
# ─────────────────────────────────────────────────────────────────────────────
class Execucao(Base):
    __tablename__ = "execucoes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    iniciado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finalizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fontes_verificadas: Mapped[list] = mapped_column(JSON, default=list)
    novas_vagas: Mapped[int] = mapped_column(Integer, default=0)
    vagas_notificadas: Mapped[int] = mapped_column(Integer, default=0)
    erros: Mapped[dict] = mapped_column(JSON, default=dict)
    caminho_historico: Mapped[str] = mapped_column(String(500), default="")  # path do run_XX.json
    perfil_reconstruido: Mapped[bool] = mapped_column(Boolean, default=False)
