import hashlib
import secrets
import time
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.security import (
    _DUMMY_PASSWORD_HASH,
    create_access_token,
    create_uuid7,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.db.database import SessionLocal
from app.models import Administrator, RefreshSession

REFRESH_SESSION_LIFETIME_SECONDS = 7 * 24 * 60 * 60


class InvalidCredentialsError(Exception):
    pass


class InvalidRefreshSessionError(Exception):
    pass


class InvalidAccessTokenError(Exception):
    pass


def authenticate_administrator(email: str, password: str) -> tuple[str, str]:
    with SessionLocal() as session:
        administrator = session.scalar(
            select(Administrator).where(Administrator.email == email)
        )
        password_hash = (
            administrator.password_hash if administrator else _DUMMY_PASSWORD_HASH
        )
        password_is_valid = verify_password(password, password_hash)

    if administrator is None or not password_is_valid:
        raise InvalidCredentialsError

    refresh_token = secrets.token_urlsafe(48)
    refresh_session_id = create_uuid7()
    with SessionLocal.begin() as session:
        session.add(
            RefreshSession(
                id=refresh_session_id,
                administrator_id=administrator.id,
                token_hash=hashlib.sha256(refresh_token.encode()).hexdigest(),
                expires_at=datetime.now(timezone.utc)
                + timedelta(seconds=REFRESH_SESSION_LIFETIME_SECONDS),
            )
        )

    access_token = create_access_token(
        administrator.id, refresh_session_id, int(time.time())
    )
    return access_token, refresh_token


def rotate_refresh_session(refresh_token: str) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        current = session.scalar(
            select(RefreshSession)
            .where(
                RefreshSession.token_hash
                == hashlib.sha256(refresh_token.encode()).hexdigest()
            )
            .with_for_update()
        )
        if current is None or current.revoked_at is not None:
            raise InvalidRefreshSessionError
        expires_at = current.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            raise InvalidRefreshSessionError

        administrator = session.scalar(
            select(Administrator)
            .options(joinedload(Administrator.academy))
            .where(Administrator.id == current.administrator_id)
        )
        if administrator is None:
            raise InvalidRefreshSessionError

        current.revoked_at = now
        new_refresh_token = secrets.token_urlsafe(48)
        new_refresh_session_id = create_uuid7()
        session.add(
            RefreshSession(
                id=new_refresh_session_id,
                administrator_id=administrator.id,
                token_hash=hashlib.sha256(new_refresh_token.encode()).hexdigest(),
                expires_at=now + timedelta(seconds=REFRESH_SESSION_LIFETIME_SECONDS),
            )
        )
        session.commit()

    access_token = create_access_token(
        administrator.id, new_refresh_session_id, int(now.timestamp())
    )
    return access_token, new_refresh_token


def revoke_refresh_session(refresh_token: str | None) -> None:
    if not refresh_token:
        return
    with SessionLocal() as session:
        current = session.scalar(
            select(RefreshSession)
            .where(
                RefreshSession.token_hash
                == hashlib.sha256(refresh_token.encode()).hexdigest()
            )
            .with_for_update()
        )
        if current is not None and current.revoked_at is None:
            current.revoked_at = datetime.now(timezone.utc)
            session.commit()


def get_administrator_session(access_token: str) -> dict[str, str]:
    try:
        claims = decode_access_token(access_token)
    except jwt.InvalidTokenError as error:
        raise InvalidAccessTokenError from error

    with SessionLocal() as session:
        refresh_session = session.scalar(
            select(RefreshSession).where(
                RefreshSession.id == claims["sid"],
                RefreshSession.administrator_id == claims["sub"],
                RefreshSession.revoked_at.is_(None),
            )
        )
        if refresh_session is None:
            raise InvalidAccessTokenError
        refresh_expires_at = refresh_session.expires_at
        if refresh_expires_at.tzinfo is None:
            refresh_expires_at = refresh_expires_at.replace(tzinfo=timezone.utc)
        if refresh_expires_at <= datetime.now(timezone.utc):
            raise InvalidAccessTokenError
        administrator = session.scalar(
            select(Administrator)
            .options(joinedload(Administrator.academy))
            .where(Administrator.id == claims["sub"])
        )
        if administrator is None:
            raise InvalidAccessTokenError
        return {
            "name": administrator.name,
            "email": administrator.email,
            "academy_name": administrator.academy.name,
        }
