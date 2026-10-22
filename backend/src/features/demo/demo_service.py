from datetime import datetime, timezone

import redis
from src.exceptions import TooManyRequestsError
from src.features.chat.chat_schema import MessageResponse
from src.features.files.file_model import Chunk
from src.features.files.file_schema import ChunkResponse
from src.settings import settings


def get_redis():
    return redis.Redis.from_url(settings.REDIS_URI)


def enforce_daily_chat_limit():
    client = get_redis()
    key = f"demo:chat:{datetime.now(timezone.utc):%Y-%m-%d}"
    count = client.incr(key)
    if count == 1:
        client.expire(key, 2 * 24 * 60 * 60)

    if count > settings.DEMO_MAX_DAILY_MESSAGES:
        raise TooManyRequestsError(
            "The shared demo has reached its daily limit of "
            f"{settings.DEMO_MAX_DAILY_MESSAGES} questions. Please try again tomorrow."
        )


def to_transient_message(
    project_id: int, answer: str, chunks: list[Chunk]
) -> MessageResponse:
    now = datetime.now(timezone.utc)
    return MessageResponse(
        id=-int(now.timestamp() * 1000),
        project_id=project_id,
        owner="assistant",
        content=answer,
        created_at=now,
        citations=[ChunkResponse.model_validate(chunk) for chunk in chunks],
    )
