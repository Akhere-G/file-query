import inspect
import time

import jwt
from starlette.requests import Request

from src.limiter import rate_limit_key
from src.settings import settings
from tests.conftest import PASSWORD

SECRET = {"X-Internal-Secret": "test-internal-secret"}


def login(client, ip):
    return client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": PASSWORD},
        headers={**SECRET, "X-Client-IP": ip},
    )


def request_with(headers, client_host="10.0.0.1"):
    return Request(
        {
            "type": "http",
            "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
            "client": (client_host, 1234),
        }
    )


def token(**claims):
    claims["exp"] = time.time() + 60
    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def test_login_is_limited_per_forwarded_ip(client):
    codes = [login(client, "203.0.113.1").status_code for _ in range(22)]
    assert codes[:20] == [401] * 20
    assert codes[20:] == [429, 429]
    assert login(client, "203.0.113.2").status_code == 401


def test_forwarded_ip_is_ignored_without_the_secret(client):
    codes = [
        client.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": PASSWORD},
            headers={"X-Client-IP": f"198.51.100.{i}"},
        ).status_code
        for i in range(22)
    ]
    assert codes[-1] == 429


def test_upload_limit_is_per_user(client, make_user):
    _, first = make_user()
    _, second = make_user()
    body = [{"name": "a.txt", "mimeType": "text/plain", "size": 5}]
    project_id = client.post("/api/files", json=body, headers=first).json()["projectId"]
    codes = [
        client.post(f"/api/files?project_id={project_id}", json=body, headers=first).status_code
        for _ in range(21)
    ]
    assert 429 in codes
    assert client.post("/api/files", json=body, headers=second).status_code == 200


def test_rate_limit_key():
    forwarded = {**SECRET, "X-Client-IP": "203.0.113.7"}
    assert rate_limit_key(request_with({})) == "ip:10.0.0.1"
    assert rate_limit_key(request_with(forwarded)) == "ip:203.0.113.7"
    assert rate_limit_key(request_with({"X-Client-IP": "203.0.113.7"})) == "ip:10.0.0.1"
    user_headers = {**forwarded, "Authorization": f"Bearer {token(sub='a@example.com')}"}
    assert rate_limit_key(request_with(user_headers)) == "user:a@example.com"
    demo_headers = {**forwarded, "Authorization": f"Bearer {token(sub='d@example.com', demo=True)}"}
    assert rate_limit_key(request_with(demo_headers)) == "ip:203.0.113.7"
    assert rate_limit_key(request_with({"Authorization": "Bearer garbage"})) == "ip:10.0.0.1"


def test_every_limited_route_is_registered_with_its_limit():
    from src.features.auth import user_routes
    from src.features.chat import chat_routes
    from src.features.files import file_routes
    from src.limiter import limiter

    registered = {}
    for module in (user_routes, chat_routes, file_routes):
        for route in module.router.routes:
            original = inspect.unwrap(route.endpoint)
            registered[f"{original.__module__}.{original.__name__}"] = route.endpoint is not original

    assert limiter._route_limits
    for name in limiter._route_limits:
        assert registered.get(name), f"{name} is not rate limited"
