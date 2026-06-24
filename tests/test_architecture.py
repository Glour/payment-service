from pathlib import Path


def test_core_responsibilities_are_split_into_focused_modules():
    root = Path(__file__).resolve().parents[1]

    expected_files = [
        "app/models/payment.py",
        "app/models/outbox.py",
        "app/models/enums.py",
        "app/schemas/payment.py",
        "app/schemas/events.py",
        "app/schemas/webhook.py",
        "app/repositories/payments.py",
        "app/repositories/outbox.py",
        "app/services/payments.py",
        "app/outbox/publisher.py",
        "app/broker/topology.py",
        "app/workers/payment_consumer.py",
    ]

    for filename in expected_files:
        assert (root / filename).exists(), filename

