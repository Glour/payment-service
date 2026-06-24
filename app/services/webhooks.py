import asyncio

import httpx

from app.schemas.webhook import WebhookPayload
from app.settings import Settings, get_settings


class WebhookDeliveryError(RuntimeError):
    pass


async def send_webhook(
    webhook_url: str,
    payload: WebhookPayload,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    last_error: Exception | None = None

    async with httpx.AsyncClient(timeout=settings.webhook_timeout_seconds) as client:
        for attempt in range(1, settings.webhook_retry_attempts + 1):
            try:
                response = await client.post(webhook_url, json=payload.model_dump(mode="json"))
                response.raise_for_status()
                return
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt < settings.webhook_retry_attempts:
                    await asyncio.sleep(2 ** (attempt - 1))

    raise WebhookDeliveryError(f"webhook delivery failed after {settings.webhook_retry_attempts} attempts") from last_error

