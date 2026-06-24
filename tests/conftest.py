import os
import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

ROOT_DIR = Path(__file__).resolve().parents[1]
TEST_DB_PATH = ROOT_DIR / ".test-payments.db"

sys.path.insert(0, str(ROOT_DIR))

os.environ["API_KEY"] = "test-api-key"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"
os.environ["ENABLE_OUTBOX_PUBLISHER"] = "false"
os.environ["GATEWAY_MIN_DELAY_SECONDS"] = "0"
os.environ["GATEWAY_MAX_DELAY_SECONDS"] = "0"

from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402


@pytest.fixture(autouse=True)
async def reset_database():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client

