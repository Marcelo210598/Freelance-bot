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

    scheduler.add_job(
        executar_ciclo,
        trigger=IntervalTrigger(minutes=cfg.freq_minutos),
        id="ciclo_principal",
        name="Coleta de vagas freelance",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "Worker iniciado. Ciclo a cada %d minutos. Rodando primeiro ciclo imediatamente...",
        cfg.freq_minutos,
    )

    # roda o primeiro ciclo imediatamente sem esperar o intervalo
    await executar_ciclo()

    # usa asyncio.Event para encerramento limpo (evita loop.stop())
    shutdown_event = asyncio.Event()

    def _encerrar(*_):
        logger.info("Sinal de encerramento recebido. Parando scheduler...")
        if scheduler.running:
            scheduler.shutdown(wait=False)
        shutdown_event.set()

    signal.signal(signal.SIGTERM, _encerrar)
    signal.signal(signal.SIGINT, _encerrar)

    logger.info("Worker aguardando próximo ciclo...")
    await shutdown_event.wait()
    logger.info("Worker encerrado.")


if __name__ == "__main__":
    asyncio.run(main())
