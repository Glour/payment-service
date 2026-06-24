import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PaymentStatus
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate
from app.time import utcnow


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, payment_id: uuid.UUID, *, for_update: bool = False) -> Payment | None:
        statement = select(Payment).where(Payment.id == payment_id)
        if for_update:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, idempotency_key: str) -> Payment | None:
        result = await self.session.execute(select(Payment).where(Payment.idempotency_key == idempotency_key))
        return result.scalar_one_or_none()

    def create_pending(self, *, payload: PaymentCreate, idempotency_key: str) -> Payment:
        payment = Payment(
            id=uuid.uuid4(),
            amount=payload.amount,
            currency=payload.currency,
            description=payload.description,
            payment_metadata=payload.metadata,
            status=PaymentStatus.PENDING,
            idempotency_key=idempotency_key,
            webhook_url=str(payload.webhook_url),
        )
        self.session.add(payment)
        return payment

    def mark_processed(self, payment: Payment, *, status: PaymentStatus) -> None:
        payment.status = status
        payment.processed_at = utcnow()

