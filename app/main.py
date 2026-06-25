import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.api import payments_router
from app.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    publisher_task: asyncio.Task[None] | None = None

    if settings.enable_outbox_publisher:
        from app.outbox.publisher import run_outbox_publisher

        publisher_task = asyncio.create_task(run_outbox_publisher(settings))

    try:
        yield
    finally:
        if publisher_task is not None:
            publisher_task.cancel()
            with suppress(asyncio.CancelledError):
                await publisher_task


def create_app() -> FastAPI:
    app = FastAPI(title="Async Payments Service", version="0.1.0", lifespan=lifespan)
    app.include_router(payments_router)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
