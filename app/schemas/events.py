from uuid import UUID

from pydantic import BaseModel


class PaymentCreatedEvent(BaseModel):
    payment_id: UUID
    attempts: int = 0


class DeadLetterEvent(BaseModel):
    payment_id: UUID
    attempts: int
    error: str

