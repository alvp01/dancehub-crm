import hashlib
import hmac
import secrets
import time
from uuid import UUID

import jwt

from app.core.config import get_settings

JWT_ISSUER = "dancehub-crm-api"
JWT_AUDIENCE = "dancehub-crm"
ACCESS_TOKEN_LIFETIME_SECONDS = 900
_FALLBACK_JWT_SIGNING_KEY = secrets.token_urlsafe(32)


def get_jwt_signing_key() -> str:
    return get_settings().jwt_secret or _FALLBACK_JWT_SIGNING_KEY


def create_uuid7() -> str:
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


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    iterations = 600_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded_hash: str) -> bool:
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


_DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))


def create_access_token(administrator_id: str, session_id: str, now: int) -> str:
    return jwt.encode(
        {
            "sub": administrator_id,
            "sid": session_id,
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
            "iat": now,
            "exp": now + ACCESS_TOKEN_LIFETIME_SECONDS,
            "jti": secrets.token_urlsafe(16),
        },
        get_jwt_signing_key(),
        algorithm="HS256",
    )


def decode_access_token(access_token: str) -> dict[str, str | int]:
    return jwt.decode(
        access_token,
        get_jwt_signing_key(),
        algorithms=["HS256"],
        audience=JWT_AUDIENCE,
        issuer=JWT_ISSUER,
        options={"require": ["sub", "sid", "exp", "iat", "jti"]},
    )


def verify_operator_secret(candidate: str | None) -> bool:
    configured_secret = get_settings().operator_secret
    return bool(configured_secret) and secrets.compare_digest(
        (candidate or "").encode("utf-8"),
        configured_secret.encode("utf-8"),
    )
