from uuid import uuid4

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models import OutboxMessage, Payment

API_HEADERS = {
    "X-API-Key": "test-api-key",
    "Idempotency-Key": "idem-001",
}


def payment_payload(**overrides):
    payload = {
        "amount": "150.25",
        "currency": "RUB",
        "description": "Order #1001",
        "metadata": {"order_id": "1001"},
        "webhook_url": "https://example.com/webhooks/payments",
    }
    payload.update(overrides)
    return payload


async def count_rows(model) -> int:
    async with SessionLocal() as session:
        result = await session.execute(select(func.count()).select_from(model))
        return result.scalar_one()


async def test_post_payment_requires_valid_api_key(client):
    response = await client.post(
        "/api/v1/payments",
        headers={"Idempotency-Key": "idem-auth"},
        json=payment_payload(),
    )
    assert response.status_code == 401

    response = await client.post(
        "/api/v1/payments",
        headers={"X-API-Key": "wrong", "Idempotency-Key": "idem-auth"},
        json=payment_payload(),
    )
    assert response.status_code == 401


async def test_create_payment_is_idempotent_and_creates_one_outbox_message(client):
    first = await client.post("/api/v1/payments", headers=API_HEADERS, json=payment_payload())
    second = await client.post("/api/v1/payments", headers=API_HEADERS, json=payment_payload(amount="999.99"))

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["payment_id"] == second.json()["payment_id"]
    assert first.json()["status"] == "pending"

    assert await count_rows(Payment) == 1
    assert await count_rows(OutboxMessage) == 1


async def test_payment_validation(client):
    response = await client.post(
        "/api/v1/payments",
        headers={"X-API-Key": "test-api-key"},
        json=payment_payload(),
    )
    assert response.status_code == 400

    response = await client.post(
        "/api/v1/payments",
        headers={**API_HEADERS, "Idempotency-Key": "idem-invalid"},
        json=payment_payload(amount="-1.00"),
    )
    assert response.status_code == 422

    response = await client.post(
        "/api/v1/payments",
        headers={**API_HEADERS, "Idempotency-Key": "idem-invalid-currency"},
        json=payment_payload(currency="GBP"),
    )
    assert response.status_code == 422


async def test_get_payment_returns_full_details(client):
    created = await client.post(
        "/api/v1/payments",
        headers={**API_HEADERS, "Idempotency-Key": "idem-read"},
        json=payment_payload(currency="USD"),
    )
    payment_id = created.json()["payment_id"]

    response = await client.get(
        f"/api/v1/payments/{payment_id}",
        headers={"X-API-Key": "test-api-key"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["payment_id"] == payment_id
    assert body["amount"] == "150.25"
    assert body["currency"] == "USD"
    assert body["description"] == "Order #1001"
    assert body["metadata"] == {"order_id": "1001"}
    assert body["status"] == "pending"
    assert body["idempotency_key"] == "idem-read"
    assert body["webhook_url"] == "https://example.com/webhooks/payments"
    assert body["processed_at"] is None


async def test_get_payment_handles_auth_and_missing_payment(client):
    payment_id = uuid4()

    response = await client.get(f"/api/v1/payments/{payment_id}")
    assert response.status_code == 401

    response = await client.get(
        f"/api/v1/payments/{payment_id}",
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 404

