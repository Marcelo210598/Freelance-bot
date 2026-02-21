"""
Ciclo completo de execução do worker:
1. Checar se GitHub mudou → rebuild de perfil
2. Coletar vagas (3 fontes)
3. Deduplicar e salvar no DB
4. Calcular score (embeddings + palavras-chave)
5. Estimar valor/prazo e montar proposta
6. Enviar alertas Telegram (top vagas acima do threshold)
7. Registrar execução no DB e em arquivo
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.coletores.base import VagaColetada
from app.coletores.freelancer import ColetorFreelancer
from app.coletores.noventa_freelas import Coletor99Freelas
from app.coletores.workana import ColetorWorkana
from app.core.database import FabricaSessao
from app.core.models import (
    Candidatura,
    Configuracao,
    Execucao,
    Perfil,
    PontuacaoVaga,
    StatusCandidatura,
    Vaga,
)
from app.historico.registro import RegistradorExecucao, garantir_devlog
from app.notificacao.telegram import DadosAlerta, NotificadorTelegram
from app.perfil.embeddings import gerar_embedding, serializar_embedding
from app.perfil.github import ConstrutorPerfil
from app.scoring.estimador import estimar
from app.scoring.matcher import calcular_score

logger = logging.getLogger(__name__)


async def executar_ciclo() -> None:
    """Ponto de entrada do ciclo. Chamado pelo scheduler."""
    garantir_devlog()
    registrador = RegistradorExecucao()
    inicio = datetime.now(timezone.utc)
    erros: dict = {}
    novas_salvas = 0
    notificadas = 0
    fontes_verificadas: list[str] = []
    perfil_reconstruido = False

    async with FabricaSessao() as sessao:
        # ── 1. carregar configurações ────────────────────────────────────
        config = await _obter_config(sessao)
        registrador.registrar_log(f"Config carregada: diaria={config.diaria_base}, threshold={config.threshold_score}")

        # ── 2. checar perfil do GitHub ────────────────────────────────────
        perfil = await _obter_perfil(sessao)
        construtor = ConstrutorPerfil()

        ultima_atualizacao = perfil.atualizado_em.isoformat() if perfil else "1970-01-01T00:00:00"
        github_mudou = await construtor.checar_mudanca_github(ultima_atualizacao)

        if github_mudou or not perfil or not perfil.embedding_b64:
            registrador.registrar_log("Reconstruindo perfil do GitHub...")
            try:
                texto_combinado = await construtor.construir_perfil_completo()
                embedding = gerar_embedding(texto_combinado)
                embedding_b64 = serializar_embedding(embedding)
                await _salvar_perfil(sessao, texto_combinado, embedding_b64)
                perfil_reconstruido = True
                registrador.registrar_log("Perfil reconstruído com sucesso.")
            except Exception as exc:
                erros["perfil"] = str(exc)
                logger.error("[ciclo] Erro ao reconstruir perfil: %s", exc)
        else:
            registrador.registrar_log("Perfil sem mudanças. Reutilizando embedding existente.")

        # recarrega perfil atualizado
        perfil = await _obter_perfil(sessao)
        if not perfil or not perfil.embedding_b64:
            registrador.registrar_log("Sem embedding de perfil. Abortando scoring.", "WARNING")
            embedding_b64 = ""
        else:
            embedding_b64 = perfil.embedding_b64

        # ── 3. coletar vagas ─────────────────────────────────────────────
        todas_vagas: list[VagaColetada] = []
        coletores = [
            Coletor99Freelas(),
            ColetorWorkana(),
            ColetorFreelancer(),
        ]

        for coletor in coletores:
            async with coletor:
                try:
                    vagas = await coletor.coletar()
                    todas_vagas.extend(vagas)
                    fontes_verificadas.append(coletor.nome)
                    registrador.registrar_log(f"[{coletor.nome}] {len(vagas)} vagas coletadas.")
                except Exception as exc:
                    erros[coletor.nome] = str(exc)
                    logger.error("[ciclo] Erro no coletor %s: %s", coletor.nome, exc)

        # ── 4. deduplicar e salvar ────────────────────────────────────────
        novas_vagas = await _deduplicar_e_salvar(sessao, todas_vagas)
        novas_salvas = len(novas_vagas)
        registrador.registrar_log(f"{novas_salvas} novas vagas salvas no banco.")

        # ── 5. calcular scores e estimativas ─────────────────────────────
        vagas_pontuadas: list[tuple[Vaga, float]] = []

        if embedding_b64 and novas_vagas:
            for vaga_modelo, vaga_coletada in novas_vagas:
                try:
                    resultado_match = calcular_score(
                        vaga_coletada,
                        __import__("app.perfil.embeddings", fromlist=["deserializar_embedding"]).deserializar_embedding(embedding_b64),
                        config.keywords_boost,
                        config.keywords_penalty,
                    )
                    resultado_estima = estimar(
                        vaga_coletada.titulo,
                        vaga_coletada.descricao,
                        config.diaria_base,
                        config.pisos_por_categoria,
                    )

                    # salvar pontuação
                    pontuacao = PontuacaoVaga(
                        vaga_id=vaga_modelo.id,
                        score=resultado_match.score,
                        similaridade=resultado_match.similaridade,
                        score_palavras=resultado_match.score_palavras,
                        complexity_score=resultado_estima.complexity_score,
                        dias_estimados=resultado_estima.dias_estimados,
                        valor_sugerido=resultado_estima.valor_sugerido,
                        motivo_match=resultado_match.motivo_match,
                        proposta_sugerida=resultado_estima.proposta,
                    )
                    sessao.add(pontuacao)

                    # candidatura inicial
                    candidatura = Candidatura(
                        vaga_id=vaga_modelo.id,
                        status=StatusCandidatura.encontrado,
                    )
                    sessao.add(candidatura)

                    if resultado_match.score >= config.threshold_score:
                        vagas_pontuadas.append((vaga_modelo, resultado_match.score))

                except Exception as exc:
                    logger.warning("[ciclo] Erro ao pontuar vaga %s: %s", vaga_modelo.id, exc)

            await sessao.commit()
            registrador.registrar_log(f"{len(vagas_pontuadas)} vagas acima do threshold ({config.threshold_score}).")

        # ── 6. enviar alertas Telegram ────────────────────────────────────
        if vagas_pontuadas and embedding_b64:
            # ordena por score desc
            vagas_pontuadas.sort(key=lambda x: x[1], reverse=True)

            # monta alertas
            alertas: list[DadosAlerta] = []
            for vaga_m, _ in vagas_pontuadas:
                pontuacao = await sessao.get(PontuacaoVaga, vaga_m.id)
                if not pontuacao:
                    continue
                alertas.append(
                    DadosAlerta(
                        titulo=vaga_m.titulo,
                        fonte=vaga_m.fonte,
                        url=vaga_m.url,
                        score=pontuacao.score,
                        complexity_score=pontuacao.complexity_score,
                        valor_sugerido=pontuacao.valor_sugerido,
                        dias_estimados=pontuacao.dias_estimados,
                        motivo_bullets=pontuacao.motivo_match.get("bullets", []),
                        proposta_curta=pontuacao.proposta_sugerida,
                    )
                )

            telegram = NotificadorTelegram()
            notificadas = await telegram.enviar_alertas(alertas)
            registrador.registrar_log(f"{notificadas} alertas enviados no Telegram.")

        # ── 7. registrar execução ─────────────────────────────────────────
        fim = datetime.now(timezone.utc)
        dados_run = {
            "iniciado_em": inicio.isoformat(),
            "finalizado_em": fim.isoformat(),
            "duracao_segundos": (fim - inicio).total_seconds(),
            "fontes_verificadas": fontes_verificadas,
            "total_vagas_coletadas": len(todas_vagas),
            "novas_vagas": novas_salvas,
            "vagas_notificadas": notificadas,
            "perfil_reconstruido": perfil_reconstruido,
            "erros": erros,
        }
        caminho = registrador.salvar(dados_run)

        execucao = Execucao(
            iniciado_em=inicio,
            finalizado_em=fim,
            fontes_verificadas=fontes_verificadas,
            novas_vagas=novas_salvas,
            vagas_notificadas=notificadas,
            erros=erros,
            caminho_historico=caminho,
            perfil_reconstruido=perfil_reconstruido,
        )
        sessao.add(execucao)
        await sessao.commit()

        registrador.registrar_log(
            f"Ciclo finalizado em {(fim - inicio).total_seconds():.1f}s. "
            f"Novas: {novas_salvas} | Notificadas: {notificadas} | Erros: {len(erros)}"
        )


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _obter_config(sessao: AsyncSession) -> Configuracao:
    cfg = (await sessao.execute(select(Configuracao).where(Configuracao.id == 1))).scalar_one_or_none()
    if not cfg:
        cfg = Configuracao(id=1)
        sessao.add(cfg)
        await sessao.commit()
        await sessao.refresh(cfg)
    return cfg


async def _obter_perfil(sessao: AsyncSession) -> Perfil | None:
    return (await sessao.execute(select(Perfil).where(Perfil.id == 1))).scalar_one_or_none()


async def _salvar_perfil(sessao: AsyncSession, texto: str, embedding_b64: str) -> None:
    perfil = await _obter_perfil(sessao)
    if perfil:
        perfil.texto_combinado = texto
        perfil.embedding_b64 = embedding_b64
    else:
        perfil = Perfil(id=1, texto_combinado=texto, embedding_b64=embedding_b64)
        sessao.add(perfil)
    await sessao.commit()


async def _deduplicar_e_salvar(
    sessao: AsyncSession, vagas: list[VagaColetada]
) -> list[tuple[Vaga, VagaColetada]]:
    """
    Salva apenas vagas novas (deduplica por fonte + external_id).
    Retorna lista de (modelo_salvo, vaga_coletada).
    """
    salvas: list[tuple[Vaga, VagaColetada]] = []

    for vc in vagas:
        # verifica se já existe
        existente = (
            await sessao.execute(
                select(Vaga)
                .where(Vaga.fonte == vc.fonte)
                .where(Vaga.external_id == vc.external_id)
            )
        ).scalar_one_or_none()

        if existente:
            continue  # deduplicada

        modelo = Vaga(
            fonte=vc.fonte,
            external_id=vc.external_id,
            url=vc.url,
            titulo=vc.titulo,
            descricao=vc.descricao,
            orcamento_raw=vc.orcamento_raw,
            publicado_em=vc.publicado_em,
            tags=vc.tags,
            raw_json=vc.raw_json,
        )
        sessao.add(modelo)
        await sessao.flush()  # gera o ID
        salvas.append((modelo, vc))

    await sessao.commit()
    return salvas
