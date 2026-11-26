import hashlib
import secrets
import time
from uuid import UUID

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.db import SessionLocal
from app.models import Academy, Administrator

settings = get_settings()
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


@app.post("/api/operator/registration", status_code=201)
def register_academy(
    registration: RegistrationRequest,
    operator_secret: str | None = Header(default=None, alias="X-Operator-Secret"),
) -> dict[str, dict[str, str]]:
    if not settings.operator_secret or not secrets.compare_digest(
        operator_secret or "", settings.operator_secret
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
