import hashlib
import hmac
import logging

from posthog import Posthog
from src.settings import settings

logger = logging.getLogger(__name__)

_client: Posthog | None = None

FILE_TYPES = {
    "application/pdf": "pdf",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
    "text/markdown": "md",
    "text/csv": "csv",
}


def file_type_label(mime_type: str) -> str:
    return FILE_TYPES.get(mime_type, "other")


def _get_client() -> Posthog | None:
    global _client

    if not settings.POSTHOG_API_KEY or not settings.POSTHOG_ID_SALT:
        return None

    if _client is None:
        _client = Posthog(settings.POSTHOG_API_KEY, host=settings.POSTHOG_HOST)

    return _client


def _distinct_id(user_id: int) -> str:
    assert settings.POSTHOG_ID_SALT
    return hmac.new(
        settings.POSTHOG_ID_SALT.encode(), str(user_id).encode(), hashlib.sha256
    ).hexdigest()


def capture(event: str, user_id: int, is_demo: bool = False, **properties):
    try:
        client = _get_client()
        if client is None:
            return

        client.capture(
            event,
            distinct_id=_distinct_id(user_id),
            properties={
                **properties,
                "is_demo": is_demo,
                "$process_person_profile": False,
            },
        )
    except Exception:
        logger.debug("Could not send analytics event %s", event, exc_info=True)


def flush():
    try:
        if _client is not None:
            _client.flush()
    except Exception:
        logger.debug("Could not flush analytics events", exc_info=True)
