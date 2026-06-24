import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox import OutboxMessage
from app.time import utcnow


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(
        self,
        *,
        aggregate_id: uuid.UUID,
        event_type: str,
        routing_key: str,
        payload: dict[str, Any],
    ) -> OutboxMessage:
        message = OutboxMessage(
            id=uuid.uuid4(),
            aggregate_id=aggregate_id,
            event_type=event_type,
            routing_key=routing_key,
            payload=payload,
        )
        self.session.add(message)
        return message

    async def list_unpublished(self, *, limit: int) -> list[OutboxMessage]:
        result = await self.session.execute(
            select(OutboxMessage)
            .where(OutboxMessage.published_at.is_(None))
            .order_by(OutboxMessage.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(result.scalars().all())

    def mark_published(self, message: OutboxMessage) -> None:
        message.published_at = utcnow()

