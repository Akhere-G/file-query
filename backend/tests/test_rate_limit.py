from src.main import app
from tests.conftest import PASSWORD

SECRET = {"X-Internal-Secret": "test-internal-secret"}


def login(client, ip=None, email="nobody@example.com"):
    headers = dict(SECRET)
    if ip:
        headers["X-Client-IP"] = ip
    return client.post(
        "/api/auth/login", json={"email": email, "password": PASSWORD}, headers=headers
    )


def test_login_is_limited_per_forwarded_ip(client):
    codes = [login(client, "203.0.113.1").status_code for _ in range(22)]
    assert codes[:20] == [401] * 20
    assert codes[20:] == [429, 429]
    # a different visitor behind the same frontend is unaffected
    assert login(client, "203.0.113.2").status_code == 401


def test_forwarded_ip_ignored_without_secret(client):
    codes = []
    for i in range(22):
        res = client.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": PASSWORD},
            headers={"X-Client-IP": f"198.51.100.{i}"},
        )
        codes.append(res.status_code)
    # spoofed addresses do not escape the real socket-address bucket
    assert codes[-1] == 429


def test_register_and_demo_are_limited(client):
    codes = [login_demo(client) for _ in range(31)]
    assert codes[-1] == 429


def login_demo(client):
    return client.post("/api/auth/demo", headers={**SECRET, "X-Client-IP": "203.0.113.9"}).status_code


def test_upload_limit_is_per_user_not_shared(client, make_user):
    _, first = make_user()
    _, second = make_user()
    body = [{"name": "a.txt", "mimeType": "text/plain", "size": 5}]
    # the project cap (3) stops uploads before the rate limit, so use an existing project
    project_id = client.post("/api/files", json=body, headers=first).json()["projectId"]
    url = f"/api/files?project_id={project_id}"
    codes = [client.post(url, json=body, headers=first).status_code for _ in range(21)]
    assert 429 in codes
    other = client.post("/api/files", json=body, headers=second)
    assert other.status_code == 200


def test_limit_decorators_wrap_registered_routes():
    """Regression: @limiter.limit above @router.post silently disables the limit."""
    import inspect

    from src.limiter import limiter

    from src.features.auth import user_routes
    from src.features.chat import chat_routes
    from src.features.files import file_routes
    from src.features.project import project_routes

    registered = {}
    for module in (user_routes, chat_routes, file_routes, project_routes):
        for route in module.router.routes:
            endpoint = getattr(route, "endpoint", None)
            if endpoint is None:
                continue
            original = inspect.unwrap(endpoint)
            registered[f"{original.__module__}.{original.__name__}"] = (
                endpoint is not original
            )

    assert limiter._route_limits
    for name in limiter._route_limits:
        assert name in registered, f"{name} is limited but not registered as a route"
        assert registered[name], f"{name} is registered without its rate limit"
