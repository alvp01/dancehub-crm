import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.config import get_settings
from app.db import SessionLocal
from app.models import Academy, Administrator, RefreshSession

settings = get_settings()
JWT_SIGNING_KEY = settings.jwt_secret or secrets.token_urlsafe(32)
JWT_ISSUER = "dancehub-crm-api"
JWT_AUDIENCE = "dancehub-crm"
ACCESS_TOKEN_LIFETIME_SECONDS = 900
REFRESH_SESSION_LIFETIME_SECONDS = 7 * 24 * 60 * 60
app = FastAPI(title="DanceHub CRM API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"message": "DanceHub CRM backend is running"}


class RegistrationRequest(BaseModel):
    academy_name: str
    academy_phone: str
    administrator_name: str
    administrator_email: str
    administrator_password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AdministratorSession(BaseModel):
    name: str
    email: str
    academy_name: str


def _uuid7() -> str:
    timestamp = time.time_ns() // 1_000_000
    random_a = secrets.randbits(12)
    random_b = secrets.randbits(62)
    value = (
        (timestamp << 80)
        | (0x7 << 76)
        | (random_a << 64)
        | (0b10 << 62)
        | random_b
    )
    return str(UUID(int=value))


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    iterations = 600_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, iterations, salt, digest = encoded_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        calculated = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt), int(iterations)
        )
        return hmac.compare_digest(calculated, bytes.fromhex(digest))
    except ValueError:
        return False


_DUMMY_PASSWORD_HASH = _hash_password(secrets.token_urlsafe(32))


@app.post("/api/auth/login")
def login(
    credentials: LoginRequest, request: Request, response: Response
) -> dict[str, str]:
    with SessionLocal() as session:
        administrator = session.scalar(
            select(Administrator).where(Administrator.email == credentials.email)
        )
        password_hash = (
            administrator.password_hash if administrator else _DUMMY_PASSWORD_HASH
        )
        password_is_valid = _verify_password(credentials.password, password_hash)

    if administrator is None or not password_is_valid:
        raise HTTPException(
            status_code=401,
            detail="Email or password is incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    refresh_token = secrets.token_urlsafe(48)
    refresh_session_id = _uuid7()
    with SessionLocal() as session:
        session.add(
            RefreshSession(
                id=refresh_session_id,
                administrator_id=administrator.id,
                token_hash=hashlib.sha256(refresh_token.encode()).hexdigest(),
                expires_at=datetime.now(timezone.utc)
                + timedelta(seconds=REFRESH_SESSION_LIFETIME_SECONDS),
            )
        )
        session.commit()
    now = int(time.time())
    access_token = jwt.encode(
        {
            "sub": administrator.id,
            "sid": refresh_session_id,
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
            "iat": now,
            "exp": now + ACCESS_TOKEN_LIFETIME_SECONDS,
            "jti": secrets.token_urlsafe(16),
        },
        JWT_SIGNING_KEY,
        algorithm="HS256",
    )
    response.set_cookie(
        key="dancehub_access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        max_age=ACCESS_TOKEN_LIFETIME_SECONDS,
        path="/api",
    )
    response.set_cookie(
        key="dancehub_refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        max_age=REFRESH_SESSION_LIFETIME_SECONDS,
        path="/api/auth",
    )
    return {"message": "Signed in."}


@app.post("/api/auth/refresh")
def refresh_session(request: Request, response: Response) -> dict[str, str]:
    refresh_token = request.cookies.get("dancehub_refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh session is invalid.")

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
            raise HTTPException(status_code=401, detail="Refresh session is invalid.")
        expires_at = current.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            raise HTTPException(status_code=401, detail="Refresh session is invalid.")

        administrator = session.scalar(
            select(Administrator)
            .options(joinedload(Administrator.academy))
            .where(Administrator.id == current.administrator_id)
        )
        if administrator is None:
            raise HTTPException(status_code=401, detail="Refresh session is invalid.")

        current.revoked_at = now
        new_refresh_token = secrets.token_urlsafe(48)
        new_refresh_session_id = _uuid7()
        session.add(
            RefreshSession(
                id=new_refresh_session_id,
                administrator_id=administrator.id,
                token_hash=hashlib.sha256(new_refresh_token.encode()).hexdigest(),
                expires_at=now + timedelta(seconds=REFRESH_SESSION_LIFETIME_SECONDS),
            )
        )
        session.commit()

    access_token = jwt.encode(
        {
            "sub": administrator.id,
            "sid": new_refresh_session_id,
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
            "iat": int(now.timestamp()),
            "exp": int(now.timestamp()) + ACCESS_TOKEN_LIFETIME_SECONDS,
            "jti": secrets.token_urlsafe(16),
        },
        JWT_SIGNING_KEY,
        algorithm="HS256",
    )
    response.set_cookie(
        key="dancehub_access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        max_age=ACCESS_TOKEN_LIFETIME_SECONDS,
        path="/api",
    )
    response.set_cookie(
        key="dancehub_refresh_token",
        value=new_refresh_token,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        max_age=REFRESH_SESSION_LIFETIME_SECONDS,
        path="/api/auth",
    )
    return {"message": "Session renewed."}


@app.post("/api/auth/logout")
def logout(request: Request, response: Response) -> dict[str, str]:
    refresh_token = request.cookies.get("dancehub_refresh_token")
    if refresh_token:
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

    response.delete_cookie(
        key="dancehub_access_token",
        path="/api",
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
    )
    response.delete_cookie(
        key="dancehub_refresh_token",
        path="/api/auth",
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
    )
    return {"message": "Signed out."}


def _get_administrator_session(request: Request) -> AdministratorSession:
    access_token = request.cookies.get("dancehub_access_token")
    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="Sign-in required.",
        )
    try:
        claims = jwt.decode(
            access_token,
            JWT_SIGNING_KEY,
            algorithms=["HS256"],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
            options={"require": ["sub", "sid", "exp", "iat", "jti"]},
        )
    except jwt.InvalidTokenError as error:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    with SessionLocal() as session:
        refresh_session = session.scalar(
            select(RefreshSession).where(
                RefreshSession.id == claims["sid"],
                RefreshSession.administrator_id == claims["sub"],
                RefreshSession.revoked_at.is_(None),
            )
        )
        if refresh_session is None:
            raise HTTPException(
                status_code=401, detail="Invalid or expired access token."
            )
        refresh_expires_at = refresh_session.expires_at
        if refresh_expires_at.tzinfo is None:
            refresh_expires_at = refresh_expires_at.replace(tzinfo=timezone.utc)
        if refresh_expires_at <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=401, detail="Invalid or expired access token."
            )
        administrator = session.scalar(
            select(Administrator)
            .options(joinedload(Administrator.academy))
            .where(Administrator.id == claims["sub"])
        )
        if administrator is None:
            raise HTTPException(status_code=401, detail="Invalid or expired access token.")
        return AdministratorSession(
            name=administrator.name,
            email=administrator.email,
            academy_name=administrator.academy.name,
        )


@app.get("/api/auth/me", response_model=AdministratorSession)
def get_current_administrator(
    administrator: AdministratorSession = Depends(_get_administrator_session),
) -> AdministratorSession:
    return administrator


@app.post("/api/operator/registration", status_code=201)
def register_academy(
    registration: RegistrationRequest,
    operator_secret: str | None = Header(default=None, alias="X-Operator-Secret"),
) -> dict[str, dict[str, str]]:
    if not settings.operator_secret or not secrets.compare_digest(
        (operator_secret or "").encode("utf-8"),
        settings.operator_secret.encode("utf-8"),
    ):
        raise HTTPException(status_code=403, detail="Access denied")

    password = registration.administrator_password
    corrections = []
    if len(password) < 12:
        corrections.append("at least 12 characters")
    if not any(character.isupper() for character in password):
        corrections.append("an uppercase letter")
    if not any(character.isdigit() for character in password):
        corrections.append("a digit")
    if not any(character in "-!#=?" for character in password):
        corrections.append("a special character from - ! # = ?")
    if corrections:
        raise HTTPException(
            status_code=422, detail="Password must include " + ", ".join(corrections)
        )

    academy = Academy(
        id=_uuid7(),
        name=registration.academy_name,
        phone=registration.academy_phone,
    )
    administrator = Administrator(
        id=_uuid7(),
        academy_id=academy.id,
        name=registration.administrator_name,
        email=registration.administrator_email,
        password_hash=_hash_password(registration.administrator_password),
    )

    try:
        with SessionLocal.begin() as session:
            session.add(academy)
            session.add(administrator)
    except IntegrityError as error:
        constraint_name = getattr(
            getattr(error.orig, "diag", None), "constraint_name", None
        )
        message = str(error.orig)
        if (
            constraint_name == "uq_academies_name_lower"
            or "uq_academies_name_lower" in message
        ):
            detail = "An academy with this name already exists."
        elif (
            constraint_name == "uq_academies_phone"
            or "academies.phone" in message
        ):
            detail = "An academy with this phone already exists."
        elif (
            constraint_name == "uq_administrators_email"
            or "administrators.email" in message
        ):
            detail = "An administrator with this email already exists."
        else:
            detail = "Registration conflicts with existing academy or administrator details."
        raise HTTPException(status_code=409, detail=detail) from error

    return {
        "academy": {
            "id": academy.id,
            "name": academy.name,
            "phone": academy.phone,
        },
        "administrator": {
            "id": administrator.id,
            "name": administrator.name,
            "email": administrator.email,
        },
    }
