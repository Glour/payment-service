import asyncio
import logging
from contextlib import suppress

from faststream.rabbit import RabbitBroker

from app.broker.publisher import publish_persistent
from app.broker.topology import PAYMENTS_EXCHANGE, ensure_rabbitmq_topology
from app.db.session import SessionLocal
from app.repositories.outbox import OutboxRepository
from app.settings import Settings, get_settings

logger = logging.getLogger(__name__)


async def publish_pending_once(settings: Settings, broker: object, batch_size: int | None = None) -> int:
    limit = batch_size or settings.outbox_batch_size
    async with SessionLocal() as session:
        async with session.begin():
            repository = OutboxRepository(session)
            messages = await repository.list_unpublished(limit=limit)
            for message in messages:
                await publish_persistent(
                    broker,
                    message.payload,
                    queue="",
                    exchange=PAYMENTS_EXCHANGE,
                    routing_key=message.routing_key,
                )
                repository.mark_published(message)
            return len(messages)


async def run_outbox_publisher(settings: Settings | None = None) -> None:
    settings = settings or get_settings()

    while True:
        broker = RabbitBroker(settings.rabbitmq_url)
        try:
            await broker.connect()
            await ensure_rabbitmq_topology(settings, broker)
            logger.info("outbox publisher started")

            while True:
                published = await publish_pending_once(settings, broker)
                if published:
                    logger.info("published %s outbox messages", published)
                await asyncio.sleep(settings.outbox_poll_interval_seconds)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("outbox publisher failed, reconnecting")
            await asyncio.sleep(settings.outbox_poll_interval_seconds)
        finally:
            with suppress(Exception):
                await broker.close()
