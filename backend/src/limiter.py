import hmac
import ipaddress

import jwt
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.settings import settings


def client_ip(request: Request) -> str:
    """Real client address.

    Browsers talk to the Next.js server, not to this API, so the socket address is the
    frontend's. The frontend forwards the visitor's address in X-Client-IP together with a
    shared secret; the header is ignored unless the secret matches.
    """
    secret = request.headers.get("x-internal-secret")
    forwarded = request.headers.get("x-client-ip")
    if (
        settings.INTERNAL_API_SECRET
        and secret
        and forwarded
        and hmac.compare_digest(secret, settings.INTERNAL_API_SECRET)
    ):
        try:
            return str(ipaddress.ip_address(forwarded.strip()))
        except ValueError:
            pass
    return get_remote_address(request)


def rate_limit_key(request: Request) -> str:
    """user:<email> for signed-in users, ip:<address> otherwise.

    Demo tokens are shared by every visitor, so they are keyed by IP like anonymous traffic.
    """
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token:
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            if payload.get("sub") and not payload.get("demo"):
                return f"user:{payload['sub']}"
        except jwt.InvalidTokenError:
            pass
    return f"ip:{client_ip(request)}"


def chat_limit(key: str) -> str:
    return "10/hour" if key.startswith("ip:") else "30/hour"


# swallow_errors: a Redis outage should not take the whole API down.
limiter = Limiter(
    key_func=rate_limit_key, storage_uri=settings.REDIS_URI, swallow_errors=True
)
