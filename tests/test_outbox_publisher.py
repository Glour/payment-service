from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.broker.topology import PAYMENT_CREATED_ROUTING_KEY, PAYMENTS_EXCHANGE
from app.db.session import SessionLocal
from app.models import Currency, OutboxMessage, Payment, PaymentStatus
from app.outbox.publisher import publish_pending_once


class RecordingBroker:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def publish(self, message: object, **kwargs: object) -> None:
        self.calls.append({"message": message, **kwargs})


async def test_publish_pending_once_publishes_persistently_and_marks_row():
    payment_id = uuid4()
    message_id = uuid4()
    payload = {"payment_id": str(payment_id), "attempts": 0}

    async with SessionLocal() as session:
        async with session.begin():
            session.add_all(
                [
                    Payment(
                        id=payment_id,
                        amount=Decimal("42.00"),
                        currency=Currency.USD,
                        payment_metadata={},
                        status=PaymentStatus.PENDING,
                        idempotency_key="outbox-publish-test",
                        webhook_url="https://example.com/webhooks/payments",
                    ),
                    OutboxMessage(
                        id=message_id,
                        aggregate_id=payment_id,
                        event_type="payment.created",
                        routing_key="payment.created",
                        payload=payload,
                    ),
                ]
            )

    broker = RecordingBroker()

    published = await publish_pending_once(SimpleNamespace(outbox_batch_size=10), broker)

    assert published == 1
    assert broker.calls[0]["message"] == payload
    assert broker.calls[0]["exchange"] == PAYMENTS_EXCHANGE
    assert broker.calls[0]["routing_key"] == PAYMENT_CREATED_ROUTING_KEY
    assert broker.calls[0]["persist"] is True

    async with SessionLocal() as session:
        message = await session.get(OutboxMessage, message_id)

    assert message is not None
    assert message.published_at is not None

    published = await publish_pending_once(SimpleNamespace(outbox_batch_size=10), broker)

    assert published == 0
    assert len(broker.calls) == 1
