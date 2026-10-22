from fastapi.testclient import TestClient

from src import main
from src.settings import settings


def test_docs_are_available_outside_production(client):
    assert client.get("/docs").status_code == 200


def test_docs_are_hidden_in_production(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    with TestClient(main.create_app()) as production:
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert production.get(path).status_code == 404
        assert production.get("/health").status_code == 200


def test_localhost_origin_is_only_allowed_outside_production(monkeypatch):
    monkeypatch.setattr(settings, "FRONTEND_URL", "https://app.example.com")
    headers = {"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"}

    with TestClient(main.create_app()) as development:
        res = development.options("/health", headers=headers)
        assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    with TestClient(main.create_app()) as production:
        res = production.options("/health", headers=headers)
        assert "access-control-allow-origin" not in res.headers
