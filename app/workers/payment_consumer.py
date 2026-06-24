import asyncio
import logging

from faststream import FastStream
from faststream.rabbit import RabbitBroker

from app.broker.publisher import publish_persistent
from app.broker.topology import (
    PAYMENT_CREATED_ROUTING_KEY,
    PAYMENTS_DEAD_QUEUE,
    PAYMENTS_EXCHANGE,
    PAYMENTS_NEW_QUEUE,
    ensure_rabbitmq_topology,
)
from app.db.session import SessionLocal
from app.models.enums import PaymentStatus
from app.models.payment import Payment
from app.repositories.payments import PaymentRepository
from app.schemas.events import DeadLetterEvent, PaymentCreatedEvent
from app.serializers import to_webhook_payload
from app.services.gateway import emulate_payment_gateway
from app.services.webhooks import send_webhook
from app.settings import Settings, get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
broker = RabbitBroker(settings.rabbitmq_url)
consumer_app = FastStream(broker)


@consumer_app.after_startup
async def declare_topology() -> None:
    await ensure_rabbitmq_topology(settings, broker)


@broker.subscriber(PAYMENTS_NEW_QUEUE, PAYMENTS_EXCHANGE)
async def handle_payment_created(event: PaymentCreatedEvent) -> None:
    try:
        await process_payment(event, settings)
    except Exception as exc:
        await publish_retry_or_dead_letter(event, exc, settings)


async def process_payment(event: PaymentCreatedEvent, settings: Settings) -> None:
    payment = await load_or_process_payment(event, settings)
    if payment is None:
        logger.warning("payment %s was not found", event.payment_id)
        return

    await send_webhook(payment.webhook_url, to_webhook_payload(payment), settings)


async def load_or_process_payment(event: PaymentCreatedEvent, settings: Settings) -> Payment | None:
    async with SessionLocal() as session:
        async with session.begin():
            repository = PaymentRepository(session)
            payment = await repository.get_by_id(event.payment_id, for_update=True)
            if payment is None:
                return None

            if payment.status == PaymentStatus.PENDING:
                status = await emulate_payment_gateway(settings)
                repository.mark_processed(payment, status=status)

            return payment


async def publish_retry_or_dead_letter(
    event: PaymentCreatedEvent,
    exc: Exception,
    settings: Settings,
) -> None:
    attempts = event.attempts + 1
    if attempts >= settings.consumer_retry_attempts:
        await ensure_rabbitmq_topology(settings, broker)
        dead_event = DeadLetterEvent(payment_id=event.payment_id, attempts=attempts, error=str(exc))
        await publish_persistent(
            broker,
            dead_event.model_dump(mode="json"),
            queue=PAYMENTS_DEAD_QUEUE,
            exchange=None,
        )
        logger.exception("payment message moved to dead queue after %s attempts", attempts)
        return

    await asyncio.sleep(2 ** (attempts - 1))
    retry_event = PaymentCreatedEvent(payment_id=event.payment_id, attempts=attempts)
    await publish_persistent(
        broker,
        retry_event.model_dump(mode="json"),
        queue="",
        exchange=PAYMENTS_EXCHANGE,
        routing_key=PAYMENT_CREATED_ROUTING_KEY,
    )
    logger.warning("payment message retry scheduled: payment_id=%s attempt=%s", event.payment_id, attempts)
