import importlib
from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.config import get_settings


@pytest.fixture
def registration_client(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'registration.db'}"
    with monkeypatch.context() as environment:
        environment.setenv("DATABASE_URL", database_url)
        environment.setenv("OPERATOR_SECRET", "test-operator-secret")
        environment.setenv("JWT_SECRET", "test-jwt-secret-with-32-bytes-minimum")
        get_settings.cache_clear()

        import app.db
        import app.main

        importlib.reload(app.db)
        main_module = importlib.reload(app.main)
        config_path = Path(__file__).resolve().parents[1] / "alembic.ini"
        command.upgrade(Config(str(config_path)), "head")
        engine = create_engine(database_url)

        with TestClient(main_module.app, base_url="https://testserver") as client:
            yield client, engine

        engine.dispose()
    get_settings.cache_clear()


def test_registers_academy_and_first_administrator_atomically_with_operator_secret(
    registration_client,
):
    client, engine = registration_client
    response = client.post(
        "/api/operator/registration",
        headers={"X-Operator-Secret": "test-operator-secret"},
        json={
            "academy_name": "Acme Dance Academy",
            "academy_phone": "+1-555-555-0100",
            "administrator_name": "Jamie Chen",
            "administrator_email": "jamie@example.com",
            "administrator_password": "DanceHub!2026",
        },
    )

    assert response.status_code == 201
    result = response.json()
    academy_id = UUID(result["academy"]["id"])
    administrator_id = UUID(result["administrator"]["id"])
    assert academy_id.version == 7

    with engine.connect() as connection:
        academy = connection.execute(
            text("SELECT name, phone FROM academies WHERE id = :id"),
            {"id": str(academy_id)},
        ).one()
        administrator = connection.execute(
            text(
                "SELECT name, email, academy_id FROM administrators "
                "WHERE id = :id"
            ),
            {"id": str(administrator_id)},
        ).one()

    assert academy == ("Acme Dance Academy", "+1-555-555-0100")
    assert administrator == (
        "Jamie Chen",
        "jamie@example.com",
        str(academy_id),
    )


def test_rejects_case_insensitive_academy_name_phone_and_administrator_email_duplicates(
    registration_client,
):
    client, engine = registration_client
    headers = {"X-Operator-Secret": "test-operator-secret"}
    original = {
        "academy_name": "Acme Dance Academy",
        "academy_phone": "+1-555-555-0100",
        "administrator_name": "Jamie Chen",
        "administrator_email": "jamie@example.com",
        "administrator_password": "DanceHub!2026",
    }

    assert (
        client.post(
            "/api/operator/registration", headers=headers, json=original
        ).status_code
        == 201
    )
    duplicates = [
        {
            **original,
            "academy_name": "acme dance academy",
            "academy_phone": "+1-555-555-0101",
            "administrator_email": "alex@example.com",
        },
        {
            **original,
            "academy_name": "Different Academy",
            "academy_phone": "+1-555-555-0100",
            "administrator_email": "alex@example.com",
        },
        {
            **original,
            "academy_name": "Another Academy",
            "academy_phone": "+1-555-555-0102",
        },
    ]

    for duplicate in duplicates:
        response = client.post(
            "/api/operator/registration", headers=headers, json=duplicate
        )
        assert response.status_code == 409

        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT COUNT(*) FROM academies")
            ).scalar_one() == 1
            assert connection.execute(
                text("SELECT COUNT(*) FROM administrators")
            ).scalar_one() == 1


@pytest.mark.parametrize(
    ("password", "correction"),
    [
        ("Dance!123", "12"),
        ("dancehub!2026", "uppercase"),
        ("DanceHub!Dance", "digit"),
        ("DanceHub2026", "special"),
    ],
)
def test_rejects_passwords_failing_each_specified_rule_with_actionable_errors(
    registration_client, password, correction
):
    client, engine = registration_client
    response = client.post(
        "/api/operator/registration",
        headers={"X-Operator-Secret": "test-operator-secret"},
        json={
            "academy_name": "Acme Dance Academy",
            "academy_phone": "+1-555-555-0100",
            "administrator_name": "Jamie Chen",
            "administrator_email": "jamie@example.com",
            "administrator_password": password,
        },
    )

    assert response.status_code == 422
    assert correction in str(response.json()).lower()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM academies")).scalar_one() == 0
        assert connection.execute(text("SELECT COUNT(*) FROM administrators")).scalar_one() == 0


@pytest.mark.parametrize(
    "headers",
    [
        [],
        [(b"X-Operator-Secret", b"wrong-secret")],
        [(b"X-Operator-Secret", b"\xe9")],
    ],
    ids=["missing", "incorrect", "non-ascii"],
)
def test_denies_registration_without_a_valid_operator_secret(
    registration_client, headers
):
    client, engine = registration_client
    response = client.post(
        "/api/operator/registration",
        headers=headers,
        json={
            "academy_name": "Acme Dance Academy",
            "academy_phone": "+1-555-555-0100",
            "administrator_name": "Jamie Chen",
            "administrator_email": "jamie@example.com",
            "administrator_password": "DanceHub!2026",
        },
    )

    assert response.status_code == 403
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM academies")).scalar_one() == 0
        assert connection.execute(text("SELECT COUNT(*) FROM administrators")).scalar_one() == 0


def test_login_sets_http_only_access_jwt_cookie(registration_client):
    client, _ = registration_client
    registration = client.post(
        "/api/operator/registration",
        headers={"X-Operator-Secret": "test-operator-secret"},
        json={
            "academy_name": "Acme Dance Academy",
            "academy_phone": "+1-555-555-0100",
            "administrator_name": "Jamie Chen",
            "administrator_email": "jamie@example.com",
            "administrator_password": "DanceHub!2026",
        },
    )
    assert registration.status_code == 201

    response = client.post(
        "/api/auth/login",
        json={"email": "jamie@example.com", "password": "DanceHub!2026"},
    )

    assert response.status_code == 200
    cookie = response.headers.get("set-cookie")
    assert cookie is not None
    assert "dancehub_access_token=" in cookie
    assert "httponly" in cookie.lower()
    assert "samesite=lax" in cookie.lower()
    assert "secure" in cookie.lower()
    assert "max-age=900" in cookie.lower()
    assert "access_token" not in response.json()


def test_valid_access_cookie_restores_profile_after_reload(registration_client):
    client, _ = registration_client
    registration = client.post(
        "/api/operator/registration",
        headers={"X-Operator-Secret": "test-operator-secret"},
        json={
            "academy_name": "Acme Dance Academy",
            "academy_phone": "+1-555-555-0100",
            "administrator_name": "Jamie Chen",
            "administrator_email": "jamie@example.com",
            "administrator_password": "DanceHub!2026",
        },
    )
    assert registration.status_code == 201

    response = client.post(
        "/api/auth/login",
        json={"email": "jamie@example.com", "password": "DanceHub!2026"},
    )

    assert response.status_code == 200
    with TestClient(
        client.app, base_url="https://testserver", cookies=client.cookies
    ) as refreshed_client:
        session = refreshed_client.get("/api/auth/me")
    assert session.status_code == 200
    assert session.json() == {
        "name": "Jamie Chen",
        "email": "jamie@example.com",
        "academy_name": "Acme Dance Academy",
    }
