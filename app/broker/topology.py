from app.settings import Settings

PAYMENTS_EXCHANGE_NAME = "payments"
PAYMENTS_NEW_QUEUE_NAME = "payments.new"
PAYMENTS_DEAD_QUEUE_NAME = "payments.dead"
PAYMENT_CREATED_ROUTING_KEY = "payment.created"

try:
    from faststream.rabbit import RabbitExchange, RabbitQueue
except ImportError:  # pragma: no cover
    RabbitExchange = None  # type: ignore[assignment]
    RabbitQueue = None  # type: ignore[assignment]


PAYMENTS_EXCHANGE = (
    RabbitExchange(PAYMENTS_EXCHANGE_NAME, durable=True) if RabbitExchange is not None else PAYMENTS_EXCHANGE_NAME
)
PAYMENTS_NEW_QUEUE = (
    RabbitQueue(PAYMENTS_NEW_QUEUE_NAME, durable=True, routing_key=PAYMENT_CREATED_ROUTING_KEY)
    if RabbitQueue is not None
    else PAYMENTS_NEW_QUEUE_NAME
)
PAYMENTS_DEAD_QUEUE = (
    RabbitQueue(PAYMENTS_DEAD_QUEUE_NAME, durable=True) if RabbitQueue is not None else PAYMENTS_DEAD_QUEUE_NAME
)


async def ensure_rabbitmq_topology(settings: Settings, broker: object | None = None) -> None:
    import aio_pika

    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange(PAYMENTS_EXCHANGE_NAME, durable=True)
        new_queue = await channel.declare_queue(PAYMENTS_NEW_QUEUE_NAME, durable=True)
        await new_queue.bind(exchange, routing_key=PAYMENT_CREATED_ROUTING_KEY)
        await channel.declare_queue(PAYMENTS_DEAD_QUEUE_NAME, durable=True)
