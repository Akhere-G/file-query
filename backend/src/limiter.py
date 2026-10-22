import hmac

import jwt
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.settings import settings


def client_ip(request: Request) -> str:
    secret = request.headers.get("x-internal-secret", "")
    forwarded = request.headers.get("x-client-ip")
    if (
        forwarded
        and settings.INTERNAL_API_SECRET
        and hmac.compare_digest(secret.encode(), settings.INTERNAL_API_SECRET.encode())
    ):
        return forwarded
    return get_remote_address(request)


def rate_limit_key(request: Request) -> str:
    _, _, token = request.headers.get("authorization", "").partition(" ")
    if token:
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            if payload.get("sub") and not payload.get("demo"):
                return f"user:{payload['sub']}"
        except jwt.InvalidTokenError:
            pass
    return f"ip:{client_ip(request)}"


limiter = Limiter(
    key_func=rate_limit_key, storage_uri=settings.REDIS_URI, swallow_errors=True
)
