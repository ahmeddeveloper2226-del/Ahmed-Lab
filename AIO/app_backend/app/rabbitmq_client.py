import aio_pika
from aio_pika.abc import AbstractRobustConnection, AbstractChannel

from .config import settings

# These start as None and get filled in once connect_rabbitmq() runs at
# startup (see main.py). Routers/services import get_rabbitmq_channel()
# rather than touching these variables directly.
_connection: AbstractRobustConnection | None = None
_channel: AbstractChannel | None = None


async def connect_rabbitmq() -> None:
    """Called once at startup. Opens a robust (auto-reconnecting) connection."""
    global _connection, _channel
    _connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    _channel = await _connection.channel()

    # Declare the queues the rest of the app will publish to / consume from,
    # so they exist even before any worker has started listening.
    await _channel.declare_queue("order.created", durable=True)
    await _channel.declare_queue("payment.confirmed", durable=True)


async def close_rabbitmq() -> None:
    """Called at shutdown (see main.py) to close the connection cleanly."""
    if _connection is not None:
        await _connection.close()


def get_rabbitmq_channel() -> AbstractChannel:
    """
    Used by anything that needs to publish a message, e.g.:
        channel = get_rabbitmq_channel()
        await channel.default_exchange.publish(
            aio_pika.Message(body=b'{"order_id": "o1"}'),
            routing_key="order.created",
        )
    """
    if _channel is None:
        raise RuntimeError("RabbitMQ channel not initialized — connect_rabbitmq() must run at startup first.")
    return _channel