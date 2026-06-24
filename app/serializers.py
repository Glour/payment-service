from app.models.payment import Payment
from app.schemas.payment import PaymentAccepted, PaymentRead
from app.schemas.webhook import WebhookPayload


def to_payment_accepted(payment: Payment) -> PaymentAccepted:
    return PaymentAccepted(
        payment_id=payment.id,
        status=payment.status,
        created_at=payment.created_at,
    )


def to_payment_read(payment: Payment) -> PaymentRead:
    return PaymentRead(
        payment_id=payment.id,
        amount=payment.amount,
        currency=payment.currency,
        description=payment.description,
        metadata=payment.payment_metadata,
        status=payment.status,
        idempotency_key=payment.idempotency_key,
        webhook_url=payment.webhook_url,
        created_at=payment.created_at,
        processed_at=payment.processed_at,
    )


def to_webhook_payload(payment: Payment) -> WebhookPayload:
    return WebhookPayload(
        payment_id=payment.id,
        amount=payment.amount,
        currency=payment.currency,
        status=payment.status,
        processed_at=payment.processed_at,
        metadata=payment.payment_metadata,
    )

