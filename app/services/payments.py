from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.broker.topology import PAYMENT_CREATED_ROUTING_KEY
from app.models.payment import Payment
from app.repositories.outbox import OutboxRepository
from app.repositories.payments import PaymentRepository
from app.schemas.payment import PaymentCreate


@dataclass(frozen=True)
class CreatePaymentResult:
    payment: Payment
    created: bool


class PaymentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.payments = PaymentRepository(session)
        self.outbox = OutboxRepository(session)

    async def create_payment(self, *, payload: PaymentCreate, idempotency_key: str) -> CreatePaymentResult:
        try:
            async with self.session.begin():
                existing = await self.payments.get_by_idempotency_key(idempotency_key)
                if existing is not None:
                    return CreatePaymentResult(payment=existing, created=False)

                payment = self.payments.create_pending(payload=payload, idempotency_key=idempotency_key)
                await self.session.flush()
                self.outbox.add(
                    aggregate_id=payment.id,
                    event_type="payment.created",
                    routing_key=PAYMENT_CREATED_ROUTING_KEY,
                    payload={"payment_id": str(payment.id), "attempts": 0},
                )
                return CreatePaymentResult(payment=payment, created=True)
        except IntegrityError:
            await self.session.rollback()
            existing = await self.payments.get_by_idempotency_key(idempotency_key)
            if existing is None:
                raise
            return CreatePaymentResult(payment=existing, created=False)

