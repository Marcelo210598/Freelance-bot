"""Criação inicial das tabelas

Revision ID: 001_initial
Revises:
Create Date: 2026-02-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── vagas ──────────────────────────────────────────────────────────────
    op.create_table(
        "vagas",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("fonte", sa.String(50), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("titulo", sa.Text(), nullable=False),
        sa.Column("descricao", sa.Text(), default=""),
        sa.Column("orcamento_raw", sa.String(255), default=""),
        sa.Column("publicado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), default=dict),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_unique_constraint("uq_vagas_fonte_external", "vagas", ["fonte", "external_id"])

    # ── pontuacoes ─────────────────────────────────────────────────────────
    op.create_table(
        "pontuacoes",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("vaga_id", sa.BigInteger(), sa.ForeignKey("vagas.id", ondelete="CASCADE"), unique=True),
        sa.Column("score", sa.Float(), default=0.0),
        sa.Column("similaridade", sa.Float(), default=0.0),
        sa.Column("score_palavras", sa.Float(), default=0.0),
        sa.Column("complexity_score", sa.Integer(), default=0),
        sa.Column("dias_estimados", sa.Integer(), default=1),
        sa.Column("valor_sugerido", sa.Float(), default=0.0),
        sa.Column("motivo_match", postgresql.JSONB(astext_type=sa.Text()), default=dict),
        sa.Column("proposta_sugerida", sa.Text(), default=""),
        sa.Column("calculado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── candidaturas ───────────────────────────────────────────────────────
    op.create_table(
        "candidaturas",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("vaga_id", sa.BigInteger(), sa.ForeignKey("vagas.id", ondelete="CASCADE"), unique=True),
        sa.Column(
            "status",
            sa.Enum(
                "encontrado", "candidatei", "em_conversa", "aceita", "recusada", "concluida",
                name="statuscandidatura",
            ),
            default="encontrado",
        ),
        sa.Column("valor_final", sa.Float(), nullable=True),
        sa.Column("prazo_final", sa.Integer(), nullable=True),
        sa.Column("notas", sa.Text(), default=""),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── perfil ─────────────────────────────────────────────────────────────
    op.create_table(
        "perfil",
        sa.Column("id", sa.Integer(), primary_key=True, default=1),
        sa.Column("github_texto", sa.Text(), default=""),
        sa.Column("override_texto", sa.Text(), default=""),
        sa.Column("texto_combinado", sa.Text(), default=""),
        sa.Column("embedding_b64", sa.Text(), default=""),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── configuracoes ──────────────────────────────────────────────────────
    op.create_table(
        "configuracoes",
        sa.Column("id", sa.Integer(), primary_key=True, default=1),
        sa.Column("diaria_base", sa.Float(), default=100.0),
        sa.Column("threshold_score", sa.Float(), default=0.45),
        sa.Column("freq_minutos", sa.Integer(), default=45),
        sa.Column("github_refresh_horas", sa.Integer(), default=8),
        sa.Column("keywords_boost", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("keywords_penalty", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("pisos_por_categoria", postgresql.JSONB(astext_type=sa.Text()), default=dict),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── execucoes ──────────────────────────────────────────────────────────
    op.create_table(
        "execucoes",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("iniciado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finalizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fontes_verificadas", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("novas_vagas", sa.Integer(), default=0),
        sa.Column("vagas_notificadas", sa.Integer(), default=0),
        sa.Column("erros", postgresql.JSONB(astext_type=sa.Text()), default=dict),
        sa.Column("caminho_historico", sa.String(500), default=""),
        sa.Column("perfil_reconstruido", sa.Boolean(), default=False),
    )


def downgrade() -> None:
    op.drop_table("execucoes")
    op.drop_table("configuracoes")
    op.drop_table("perfil")
    op.drop_table("candidaturas")
    op.drop_table("pontuacoes")
    op.drop_table("vagas")
    op.execute("DROP TYPE IF EXISTS statuscandidatura")
