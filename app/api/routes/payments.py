from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_api_key
from app.db.session import get_session
from app.repositories.payments import PaymentRepository
from app.schemas.payment import PaymentAccepted, PaymentCreate, PaymentRead
from app.serializers import to_payment_accepted, to_payment_read
from app.services.payments import PaymentService

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_api_key)])


@router.post("/payments", response_model=PaymentAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_payment_endpoint(
    payload: PaymentCreate,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=128),
    session: AsyncSession = Depends(get_session),
) -> PaymentAccepted:
    if not idempotency_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Idempotency-Key header is required")

    result = await PaymentService(session).create_payment(payload=payload, idempotency_key=idempotency_key)
    response.status_code = status.HTTP_202_ACCEPTED
    return to_payment_accepted(result.payment)


@router.get("/payments/{payment_id}", response_model=PaymentRead)
async def get_payment_endpoint(
    payment_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> PaymentRead:
    payment = await PaymentRepository(session).get_by_id(payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return to_payment_read(payment)

