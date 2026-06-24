from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import httpx

from app.models import Currency, PaymentStatus
from app.schemas.webhook import WebhookPayload
from app.services.webhooks import send_webhook


class FlakyAsyncClient:
    def __init__(self) -> None:
        self.requests: list[dict[str, object]] = []

    async def __aenter__(self) -> "FlakyAsyncClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def post(self, url: str, json: dict[str, object]) -> httpx.Response:
        request = httpx.Request("POST", url, json=json)
        self.requests.append({"url": url, "json": json})
        if len(self.requests) < 3:
            raise httpx.ConnectError("temporary failure", request=request)
        return httpx.Response(200, request=request)


async def test_send_webhook_retries_before_success(monkeypatch):
    client = FlakyAsyncClient()
    sleeps: list[int] = []

    def build_client(timeout: float) -> FlakyAsyncClient:
        assert timeout == 0.1
        return client

    async def fake_sleep(delay: int) -> None:
        sleeps.append(delay)

    monkeypatch.setattr("app.services.webhooks.httpx.AsyncClient", build_client)
    monkeypatch.setattr("app.services.webhooks.asyncio.sleep", fake_sleep)

    await send_webhook(
        "https://example.com/webhooks/payments",
        WebhookPayload(
            payment_id=uuid4(),
            amount=Decimal("10.00"),
            currency=Currency.RUB,
            status=PaymentStatus.SUCCEEDED,
            processed_at=None,
            metadata={"order_id": "retry-test"},
        ),
        SimpleNamespace(webhook_timeout_seconds=0.1, webhook_retry_attempts=3),
    )

    assert len(client.requests) == 3
    assert sleeps == [1, 2]

