import asyncio
import random

from app.models.enums import PaymentStatus
from app.settings import Settings


async def emulate_payment_gateway(settings: Settings) -> PaymentStatus:
    delay = random.uniform(settings.gateway_min_delay_seconds, settings.gateway_max_delay_seconds)
    await asyncio.sleep(delay)
    return PaymentStatus.SUCCEEDED if random.random() < settings.payment_success_rate else PaymentStatus.FAILED

