# Async Payments Service

FastAPI service for asynchronous payment processing. The API accepts a payment request, stores the payment and an outbox event in one database transaction, publishes the event to RabbitMQ, and a single consumer emulates an external payment gateway before sending a webhook with the final result.

## Stack

- Python 3.12
- FastAPI, Pydantic v2
- SQLAlchemy 2 async, asyncpg
- PostgreSQL, Alembic
- RabbitMQ, FastStream
- pytest with async SQLite for local tests

## Architecture

The code is split by responsibility:

```text
app/
  api/                 HTTP routes and auth dependencies
  broker/              RabbitMQ topology and persistent publishing
  db/                  async SQLAlchemy engine/session
  models/              SQLAlchemy entities and enums
  outbox/              outbox polling publisher
  repositories/        database access
  schemas/             API, event and webhook DTOs
  services/            payment creation, gateway emulation, webhooks
  workers/             FastStream consumer
```

Payment creation uses an idempotency key. A new payment and the `payment.created` outbox event are committed together. The outbox publisher later sends the event to RabbitMQ with persistent delivery. The consumer processes the message, updates the payment status, sends a webhook, retries failed messages with exponential delay, and publishes final failures to the `payments.dead` dead-letter queue after 3 consumer attempts. `WEBHOOK_RETRY_ATTEMPTS` is kept separate and defaults to `1` so the assignment-level retry budget is controlled by message retries.

## Run with Docker

```bash
cp .env.example .env
docker compose up --build
```

Services:

- API: `http://localhost:8000`
- RabbitMQ Management UI: `http://localhost:15672`
- RabbitMQ default login: `guest` / `guest`

The `migrate` service runs `alembic upgrade head` before the API and consumer start.

If a port is busy:

```bash
API_PORT=18000 RABBITMQ_PORT=25672 RABBITMQ_MANAGEMENT_PORT=25673 docker compose up --build
```

## Local Development

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
alembic upgrade head
uvicorn app.main:app --reload
```

Consumer:

```bash
faststream run app.workers.payment_consumer:consumer_app
```

Outbox publisher inside the API process is enabled by:

```bash
export ENABLE_OUTBOX_PUBLISHER=true
```

## Tests

Tests use async SQLite and do not require Docker:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
pytest -q
```

## Environment

- `API_KEY`: static key required in `X-API-Key`
- `DATABASE_URL`: SQLAlchemy async database URL
- `RABBITMQ_URL`: RabbitMQ URL
- `ENABLE_OUTBOX_PUBLISHER`: starts outbox polling in API process
- `OUTBOX_POLL_INTERVAL_SECONDS`: outbox polling interval
- `OUTBOX_BATCH_SIZE`: outbox rows per publishing iteration
- `WEBHOOK_TIMEOUT_SECONDS`: webhook request timeout
- `WEBHOOK_RETRY_ATTEMPTS`: per-message HTTP delivery attempts for a webhook call
- `CONSUMER_RETRY_ATTEMPTS`: message attempts before dead-lettering; defaults to 3
- `GATEWAY_MIN_DELAY_SECONDS`, `GATEWAY_MAX_DELAY_SECONDS`: gateway emulation delay
- `PAYMENT_SUCCESS_RATE`: gateway success probability
- `SQL_ECHO`: SQLAlchemy query logging

## API Examples

Create payment:

```bash
curl -i -X POST http://localhost:8000/api/v1/payments \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-api-key' \
  -H 'Idempotency-Key: order-1001' \
  -d '{
    "amount": "150.25",
    "currency": "RUB",
    "description": "Order #1001",
    "metadata": {"order_id": "1001"},
    "webhook_url": "https://example.com/webhooks/payments"
  }'
```

Response:

```json
{
  "payment_id": "7d0b6089-2827-45a7-b6d6-f9d90bdbf5e6",
  "status": "pending",
  "created_at": "2026-06-24T12:00:00Z"
}
```

Get payment:

```bash
curl -i http://localhost:8000/api/v1/payments/7d0b6089-2827-45a7-b6d6-f9d90bdbf5e6 \
  -H 'X-API-Key: dev-api-key'
```

Health:

```bash
curl -i http://localhost:8000/health
```
