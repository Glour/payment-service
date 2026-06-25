from pathlib import Path

from app.broker.publisher import publish_persistent
from app.broker.topology import PAYMENTS_DEAD_QUEUE_NAME
from app.models.payment import Payment
from app.repositories.payments import PaymentRepository


ROOT = Path(__file__).resolve().parents[1]


def test_prior_review_complaints_stay_fixed():
    assert not (ROOT / "app/models.py").exists()
    assert not (ROOT / "app/schemas.py").exists()

    assert hasattr(Payment, "processed_at")
    assert PAYMENTS_DEAD_QUEUE_NAME == "payments.dead"
    assert callable(publish_persistent)
    assert hasattr(PaymentRepository, "get_by_idempotency_key")

