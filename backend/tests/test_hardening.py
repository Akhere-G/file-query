from fastapi.testclient import TestClient

from src import main
from src.settings import settings


def test_docs_are_available_outside_production(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_docs_are_hidden_in_production(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    app = main.create_app()
    with TestClient(app) as production:
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert production.get(path).status_code == 404
        assert production.get("/health").status_code == 200


def test_localhost_origin_only_allowed_outside_production(monkeypatch):
    assert "http://localhost:3000" in main.allowed_origins()
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "FRONTEND_URL", "https://app.example.com")
    assert main.allowed_origins() == ["https://app.example.com"]
