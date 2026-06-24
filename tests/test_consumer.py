from types import SimpleNamespace
from uuid import uuid4

from app.schemas.events import PaymentCreatedEvent
from app.workers.payment_consumer import publish_retry_or_dead_letter


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
