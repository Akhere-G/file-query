import logging
from datetime import datetime, timezone

from src.exceptions import TooManyRequestsError
from src.features.chat.chat_schema import MessageResponse
from src.features.files.file_model import Chunk
from src.features.files.file_schema import ChunkResponse
from src.settings import settings

logger = logging.getLogger(__name__)

_redis_client = None


def _redis():
    """Redis client, or None when REDIS_URI is not a redis URL (for example in tests)."""
    global _redis_client
    if not settings.REDIS_URI.startswith(("redis://", "rediss://", "unix://")):
        return None
    if _redis_client is None:
        import redis

        _redis_client = redis.Redis.from_url(settings.REDIS_URI)
    return _redis_client


def enforce_daily_chat_limit():
    """The demo is one shared account and its chats are not saved, so the usual
    per-user monthly count in the database cannot cap it. Count in Redis instead."""
    client = _redis()
    if client is None:
        return

    key = f"demo:chat:{datetime.now(timezone.utc):%Y-%m-%d}"
    try:
        count = client.incr(key)
        if count == 1:
            client.expire(key, 2 * 24 * 60 * 60)
    except Exception:
        logger.warning("Could not check the demo chat limit", exc_info=True)
        return

    if count > settings.DEMO_MAX_DAILY_MESSAGES:
        raise TooManyRequestsError(
            "The shared demo has reached its daily limit of "
            f"{settings.DEMO_MAX_DAILY_MESSAGES} questions. Please try again tomorrow."
        )


def to_transient_message(
    project_id: int, answer: str, chunks: list[Chunk]
) -> MessageResponse:
    """An answer that is returned to the visitor but never written to the database."""
    now = datetime.now(timezone.utc)
    return MessageResponse(
        id=-int(now.timestamp() * 1000),
        project_id=project_id,
        owner="assistant",
        content=answer,
        created_at=now,
        citations=[ChunkResponse.model_validate(chunk) for chunk in chunks],
    )
