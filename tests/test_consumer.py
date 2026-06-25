from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.db.session import SessionLocal
from app.models import Currency, Payment, PaymentStatus
from app.schemas.events import PaymentCreatedEvent
from app.workers.payment_consumer import process_payment, publish_retry_or_dead_letter


class RecordingBroker:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def publish(self, message: object, **kwargs: object) -> None:
        self.calls.append({"message": message, **kwargs})


async def test_consumer_republishes_retry_before_dead_letter(monkeypatch):
    broker = RecordingBroker()
    sleeps: list[int] = []
    payment_id = uuid4()

    async def fake_sleep(delay: int) -> None:
        sleeps.append(delay)

    monkeypatch.setattr("app.workers.payment_consumer.broker", broker)
    monkeypatch.setattr("app.workers.payment_consumer.asyncio.sleep", fake_sleep)

    await publish_retry_or_dead_letter(
        PaymentCreatedEvent(payment_id=payment_id, attempts=0),
        RuntimeError("temporary"),
        SimpleNamespace(consumer_retry_attempts=3, rabbitmq_url="amqp://guest:guest@localhost/"),
    )

    assert sleeps == [1]
    assert broker.calls[0]["message"] == {"payment_id": str(payment_id), "attempts": 1}
    assert broker.calls[0]["routing_key"] == "payment.created"
    assert broker.calls[0]["persist"] is True


async def test_consumer_publishes_dead_letter_after_max_attempts(monkeypatch):
    broker = RecordingBroker()
    payment_id = uuid4()
    topology_calls: list[object] = []

    async def fake_topology(settings, broker):
        topology_calls.append((settings, broker))

    monkeypatch.setattr("app.workers.payment_consumer.broker", broker)
    monkeypatch.setattr("app.workers.payment_consumer.ensure_rabbitmq_topology", fake_topology)

    await publish_retry_or_dead_letter(
        PaymentCreatedEvent(payment_id=payment_id, attempts=2),
        RuntimeError("boom"),
        SimpleNamespace(consumer_retry_attempts=3, rabbitmq_url="amqp://guest:guest@localhost/"),
    )

    assert topology_calls
    assert broker.calls[0]["message"] == {
        "payment_id": str(payment_id),
        "attempts": 3,
        "error": "boom",
    }
    assert broker.calls[0]["persist"] is True


async def test_consumer_processes_payment_and_sends_webhook(monkeypatch):
    payment_id = uuid4()
    webhook_calls: list[object] = []

    async with SessionLocal() as session:
        async with session.begin():
            session.add(
                Payment(
                    id=payment_id,
                    amount=Decimal("99.90"),
                    currency=Currency.EUR,
                    payment_metadata={"order_id": "consumer-test"},
                    status=PaymentStatus.PENDING,
                    idempotency_key="consumer-process-test",
                    webhook_url="https://example.com/webhook",
                )
            )

    async def fake_gateway(settings):
        return PaymentStatus.SUCCEEDED

    async def fake_webhook(url, payload, settings):
        webhook_calls.append((url, payload, settings))

    monkeypatch.setattr("app.workers.payment_consumer.emulate_payment_gateway", fake_gateway)
    monkeypatch.setattr("app.workers.payment_consumer.send_webhook", fake_webhook)

    settings = SimpleNamespace(
        gateway_min_delay_seconds=0,
        gateway_max_delay_seconds=0,
        payment_success_rate=1,
    )
    await process_payment(PaymentCreatedEvent(payment_id=payment_id), settings)

    async with SessionLocal() as session:
        payment = await session.get(Payment, payment_id)

    assert payment is not None
    assert payment.status == PaymentStatus.SUCCEEDED
    assert payment.processed_at is not None
    assert len(webhook_calls) == 1
    assert webhook_calls[0][0] == "https://example.com/webhook"
    assert webhook_calls[0][1].payment_id == payment_id
    assert webhook_calls[0][1].status == PaymentStatus.SUCCEEDED
