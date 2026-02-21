"""
Estimador de complexidade, prazo e valor para cada vaga.

Heurísticas baseadas em sinais textuais (palavras-chave de complexidade).
Categorias:
  0-25   → simples       (~1-3 dias)
  26-50  → médio         (~4-10 dias)
  51-75  → complexo      (~11-20 dias)
  76-100 → muito_complexo (~21+ dias)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ── Sinais de complexidade ────────────────────────────────────────────────────
SINAIS_COMPLEXIDADE: list[tuple[list[str], int]] = [
    # (palavras, peso_de_complexidade)
    # Alta complexidade
    (["websocket", "tempo real", "realtime", "real-time"], 20),
    (["docker", "kubernetes", "k8s", "container"], 15),
    (["deploy", "ci/cd", "devops", "pipeline"], 15),
    (["integrações", "integração", "integration", "webhook"], 10),
    (["do zero", "from scratch", "novo sistema", "novo projeto"], 10),
    (["crm", "erp", "sistema completo"], 20),
    (["pagamento", "pagamentos", "stripe", "pix", "boleto"], 15),
    (["painel", "dashboard", "admin", "adminpanel"], 10),
    (["app mobile", "ios", "android", "react native", "flutter"], 20),
    (["machine learning", "ia", "ai", "inteligência artificial", "llm"], 25),
    (["microserviços", "microservices", "arquitetura"], 20),
    (["autenticação", "auth", "oauth", "sso", "jwt"], 10),
    (["banco de dados", "database", "postgres", "mysql", "mongodb"], 5),
    # Média complexidade
    (["responsivo", "responsive", "mobile-first"], 8),
    (["cross-browser", "compatibilidade"], 8),
    (["api", "rest", "graphql", "endpoint"], 8),
    (["scraping", "crawler", "selenium", "playwright"], 12),
    (["bot", "automação", "automation"], 12),
    # Baixa complexidade → reduz score
    (["landing page", "lp", "página simples", "formulário"], -15),
    (["pequena alteração", "pequena mudança", "ajuste", "ajustes"], -20),
    (["bug", "bugs", "erro", "erros", "corrigir"], 5),
    (["estabilizar", "otimizar", "melhoria"], 8),
]

# Limites de dias por categoria
DIAS_POR_CATEGORIA = {
    "simples": (1, 3),
    "medio": (4, 10),
    "complexo": (11, 20),
    "muito_complexo": (21, 45),
}


@dataclass
class ResultadoEstimativa:
    complexity_score: int       # 0–100
    categoria: str              # simples | medio | complexo | muito_complexo
    dias_estimados: int
    valor_sugerido: float       # R$
    proposta: str               # texto sugerido em PT-BR


def estimar(
    titulo: str,
    descricao: str,
    diaria_base: float,
    pisos: dict[str, float],
) -> ResultadoEstimativa:
    """
    Estima complexidade, dias e valor para uma vaga.
    """
    texto = f"{titulo} {descricao}".lower()

    # ── calcular pontuação bruta ──────────────────────────────────────────
    pontuacao_bruta = 30  # base
    for palavras, peso in SINAIS_COMPLEXIDADE:
        for palavra in palavras:
            if re.search(r"\b" + re.escape(palavra) + r"\b", texto):
                pontuacao_bruta += peso
                break  # conta cada grupo uma vez

    complexity_score = max(0, min(100, pontuacao_bruta))

    # ── categoria e dias ──────────────────────────────────────────────────
    if complexity_score <= 25:
        categoria = "simples"
    elif complexity_score <= 50:
        categoria = "medio"
    elif complexity_score <= 75:
        categoria = "complexo"
    else:
        categoria = "muito_complexo"

    min_dias, max_dias = DIAS_POR_CATEGORIA[categoria]
    # interpola dentro da faixa da categoria
    faixa = max_dias - min_dias
    posicao = (complexity_score % 25) / 25  # 0–1 dentro da categoria
    dias_estimados = round(min_dias + posicao * faixa)
    dias_estimados = max(min_dias, min(max_dias, dias_estimados))

    # ── valor sugerido ────────────────────────────────────────────────────
    valor_calculado = dias_estimados * diaria_base
    piso = pisos.get(categoria, 0.0)
    valor_sugerido = max(valor_calculado, piso)

    # ── proposta sugerida ─────────────────────────────────────────────────
    proposta = _gerar_proposta(titulo, categoria, dias_estimados, valor_sugerido)

    return ResultadoEstimativa(
        complexity_score=complexity_score,
        categoria=categoria,
        dias_estimados=dias_estimados,
        valor_sugerido=round(valor_sugerido, 2),
        proposta=proposta,
    )


def _gerar_proposta(titulo: str, categoria: str, dias: int, valor: float) -> str:
    """Template de proposta em PT-BR, curto e direto."""
    intro = {
        "simples": "Olá! Analisei a demanda e acredito que posso entregar isso com qualidade.",
        "medio": "Olá! Li o projeto com atenção e tenho experiência direta com esse tipo de solução.",
        "complexo": "Olá! Projetos como esse são exatamente minha especialidade — já trabalhei em soluções similares.",
        "muito_complexo": "Olá! Esse é um projeto robusto e tenho o stack técnico necessário para entregá-lo com excelência.",
    }.get(categoria, "Olá!")

    prazo_texto = f"{dias} dia{'s' if dias > 1 else ''} útil{'s' if dias > 1 else ''}"
    valor_texto = f"R$ {valor:,.0f}".replace(",", ".")

    return (
        f"{intro}\n\n"
        f"Baseado nos requisitos de **{titulo}**, minha proposta é:\n"
        f"- **Prazo estimado:** {prazo_texto}\n"
        f"- **Investimento:** {valor_texto}\n\n"
        f"Posso ajustar o escopo conforme suas prioridades. "
        f"Você pode ver meu portfólio e projetos anteriores no meu perfil.\n\n"
        f"Quando podemos conversar para alinhar os detalhes?"
    )
