async def publish_persistent(
    broker: object,
    message: object,
    *,
    queue: object = "",
    exchange: object | None = None,
    routing_key: str = "",
) -> None:
    publish = getattr(broker, "publish")
    kwargs = {"queue": queue, "persist": True}
    if exchange is not None:
        kwargs["exchange"] = exchange
    if routing_key:
        kwargs["routing_key"] = routing_key
    await publish(message, **kwargs)
