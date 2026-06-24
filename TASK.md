# Test Assignment Summary

Implement an asynchronous payment processing microservice.

## Required API

- `POST /api/v1/payments`
  - requires `X-API-Key`
  - requires `Idempotency-Key`
  - accepts amount, currency, description, metadata and `webhook_url`
  - returns `202 Accepted`, `payment_id`, status and `created_at`
- `GET /api/v1/payments/{payment_id}`
  - requires `X-API-Key`
  - returns full payment details

## Payment Fields

- unique payment ID
- decimal amount
- currency: `RUB`, `USD`, `EUR`
- description
- JSON metadata
- status: `pending`, `succeeded`, `failed`
- unique idempotency key
- webhook URL
- creation and processing timestamps

## Async Processing

- payment creation writes a payment and an outbox event in one DB transaction
- outbox publisher sends `payment.created` to RabbitMQ
- one consumer reads `payments.new`
- consumer emulates a gateway delay, updates status and sends webhook
- webhook/message failures retry up to 3 attempts with exponential backoff
- final failures go to `payments.dead`

## Technology Requirements

- FastAPI + Pydantic v2
- SQLAlchemy 2 async
- PostgreSQL
- RabbitMQ + FastStream
- Alembic
- Docker + docker-compose
- README with launch instructions and API examples

