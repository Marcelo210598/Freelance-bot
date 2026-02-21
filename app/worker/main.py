"""
Entry-point do Worker (Railway — serviço 2).
APScheduler executa o ciclo a cada N minutos (configurável).
"""

import asyncio
import logging
import signal
import sys

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import obter_config
from app.historico.registro import garantir_devlog
from app.worker.ciclo import executar_ciclo

logging.basicConfig(
    level=obter_config().log_level,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    cfg = obter_config()
    garantir_devlog()

    scheduler = AsyncIOScheduler()

    # ── job principal: coleta de vagas ────────────────────────────────────
    scheduler.add_job(
        executar_ciclo,
        trigger=IntervalTrigger(minutes=cfg.freq_minutos),
        id="ciclo_principal",
        name="Coleta de vagas freelance",
        max_instances=1,      # evita sobreposição
        coalesce=True,        # se atrasou, roda uma única vez
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "Worker iniciado. Ciclo a cada %d minutos. Rodando primeiro ciclo imediatamente...",
        cfg.freq_minutos,
    )

    # roda o primeiro ciclo imediatamente sem esperar o intervalo
    await executar_ciclo()

    # mantém o processo vivo
    loop = asyncio.get_event_loop()

    def _encerrar(*_):
        logger.info("Sinal de encerramento recebido. Parando scheduler...")
        scheduler.shutdown(wait=False)
        loop.stop()

    signal.signal(signal.SIGTERM, _encerrar)
    signal.signal(signal.SIGINT, _encerrar)

    try:
        await asyncio.Event().wait()  # bloqueia para sempre
    except asyncio.CancelledError:
        pass
    finally:
        scheduler.shutdown(wait=True)
        logger.info("Worker encerrado.")


if __name__ == "__main__":
    asyncio.run(main())
