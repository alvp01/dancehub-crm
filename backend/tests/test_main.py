from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app


def test_health_endpoint() -> None:
    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"message": "DanceHub CRM backend is running"}


def test_jwt_signing_secret_is_loaded_from_environment(monkeypatch) -> None:
    secret = "s" * 32
    monkeypatch.setenv("JWT_SECRET", secret)

    settings = Settings(_env_file=None)

    assert settings.jwt_secret == secret
