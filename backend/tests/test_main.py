import asyncio

import pytest
from sqlalchemy.exc import OperationalError
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.availability import database_availability
from app.db import lifecycle
from app.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"message": "DanceHub CRM backend is running"}
    assert client.get("/api/health").status_code == 404


def test_jwt_signing_secret_is_loaded_from_environment(monkeypatch) -> None:
    secret = "s" * 32
    monkeypatch.setenv("JWT_SECRET", secret)

    settings = Settings(_env_file=None)

    assert settings.jwt_secret == secret


def test_database_outage_keeps_liveness_up_and_returns_service_unavailable(
    monkeypatch,
) -> None:
    monkeypatch.setattr(database_availability, "ready", False)
    client = TestClient(app)

    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/ready").status_code == 503
    assert client.post("/api/v1/auth/refresh").status_code == 503


def test_database_monitor_retries_and_migrates_after_connection_recovers(
    monkeypatch,
) -> None:
    attempts = 0
    migrations = 0
    sleeps = 0

    def check_database_connection() -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OperationalError("SELECT 1", {}, RuntimeError("database down"))

    def apply_database_migrations() -> None:
        nonlocal migrations
        migrations += 1

    async def stop_after_recovery(_: float) -> None:
        nonlocal sleeps
        sleeps += 1
        if sleeps == 2:
            raise asyncio.CancelledError

    monkeypatch.setattr(
        lifecycle,
        "get_settings",
        lambda: Settings(
            _env_file=None,
            database_retry_initial_seconds=0.01,
            database_retry_max_seconds=0.02,
            database_health_check_interval_seconds=10,
        ),
    )
    monkeypatch.setattr(
        lifecycle, "check_database_connection", check_database_connection
    )
    monkeypatch.setattr(
        lifecycle, "apply_database_migrations", apply_database_migrations
    )
    monkeypatch.setattr(lifecycle.engine, "dispose", lambda: None)
    monkeypatch.setattr(lifecycle.asyncio, "sleep", stop_after_recovery)
    monkeypatch.setattr(database_availability, "ready", False)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(lifecycle.monitor_database())

    assert attempts == 3
    assert migrations == 1
    assert database_availability.ready
