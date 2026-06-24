from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import Currency, PaymentStatus


class WebhookPayload(BaseModel):
    payment_id: UUID
    amount: Decimal
    currency: Currency
    status: PaymentStatus
    processed_at: datetime | None
    metadata: dict[str, Any]

