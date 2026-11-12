import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from src.main import create_app
from src.settings import settings


@pytest.fixture
def app():
    app = create_app()

    @app.get("/__boom")
    def boom():
        raise RuntimeError("secret internal detail: db password is hunter2")

    @app.get("/__db_down")
    def db_down():
        raise OperationalError("SELECT 1", {}, Exception("connection refused to 10.0.0.5"))

    return app


@pytest.fixture
def http(app):
    return TestClient(app, raise_server_exceptions=False)


def test_unexpected_errors_return_a_generic_500_without_leaking_details(http):
    res = http.get("/__boom")

    assert res.status_code == 500
    assert res.json() == {"detail": "Something went wrong. Please try again."}
    assert "hunter2" not in res.text


def test_database_outages_return_503_without_leaking_details(http):
    res = http.get("/__db_down")

    assert res.status_code == 503
    assert "10.0.0.5" not in res.text


def test_health_check(http):
    assert http.get("/health").json() == {"status": "ok"}


def test_api_documentation_is_available_outside_production(http):
    assert http.get("/docs").status_code == 200


def test_api_documentation_is_hidden_in_production(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    http = TestClient(create_app(), raise_server_exceptions=False)

    assert http.get("/docs").status_code == 404
    assert http.get("/redoc").status_code == 404
    assert http.get("/openapi.json").status_code == 404


def test_cors_only_allows_the_frontend_origin(http):
    allowed = http.options(
        "/health",
        headers={"Origin": settings.FRONTEND_URL, "Access-Control-Request-Method": "GET"},
    )
    denied = http.options(
        "/health",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )

    assert allowed.headers.get("access-control-allow-origin") == settings.FRONTEND_URL
    assert "access-control-allow-origin" not in denied.headers


def test_production_cors_does_not_allow_localhost(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "FRONTEND_URL", "https://app.example.com")
    http = TestClient(create_app())

    def preflight(origin):
        return http.options(
            "/health", headers={"Origin": origin, "Access-Control-Request-Method": "GET"}
        )

    assert preflight("https://app.example.com").headers["access-control-allow-origin"] == "https://app.example.com"
    assert "access-control-allow-origin" not in preflight("http://localhost:3000").headers


def test_validation_errors_are_422_with_field_details(http):
    res = http.post("/api/auth/register", json={"email": "nope"})

    assert res.status_code == 422
    assert res.json()["detail"]


@pytest.mark.xfail(
    strict=True,
    reason="Known bug: file_embedding_worker_local omits project_id and is_last, so process_file "
    "raises KeyError on job['is_last'] after embedding",
)
def test_local_worker_cli_builds_a_complete_job():
    """The CLI must pass everything process_file reads (project_id, is_last)."""
    import inspect

    from src import file_embedding_worker_local as local
    from src.features.files.file_processing_service import FileJob

    source = inspect.getsource(local.main)
    missing = [key for key in FileJob.__annotations__ if f'"{key}"' not in source]
    assert missing == []
