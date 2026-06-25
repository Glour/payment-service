from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    api_key: str = Field(default="dev-api-key", validation_alias="API_KEY")
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/payments",
        validation_alias="DATABASE_URL",
    )
    rabbitmq_url: str = Field(default="amqp://guest:guest@localhost:5672/", validation_alias="RABBITMQ_URL")
    enable_outbox_publisher: bool = Field(default=False, validation_alias="ENABLE_OUTBOX_PUBLISHER")
    outbox_poll_interval_seconds: float = Field(default=1.0, validation_alias="OUTBOX_POLL_INTERVAL_SECONDS")
    outbox_batch_size: int = Field(default=100, validation_alias="OUTBOX_BATCH_SIZE")
    webhook_timeout_seconds: float = Field(default=5.0, validation_alias="WEBHOOK_TIMEOUT_SECONDS")
    webhook_retry_attempts: int = Field(default=1, validation_alias="WEBHOOK_RETRY_ATTEMPTS")
    consumer_retry_attempts: int = Field(default=3, validation_alias="CONSUMER_RETRY_ATTEMPTS")
    gateway_min_delay_seconds: float = Field(default=2.0, validation_alias="GATEWAY_MIN_DELAY_SECONDS")
    gateway_max_delay_seconds: float = Field(default=5.0, validation_alias="GATEWAY_MAX_DELAY_SECONDS")
    payment_success_rate: float = Field(default=0.9, ge=0, le=1, validation_alias="PAYMENT_SUCCESS_RATE")
    sql_echo: bool = Field(default=False, validation_alias="SQL_ECHO")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
