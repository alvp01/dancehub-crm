from sqlalchemy.exc import IntegrityError

from app.core.security import create_uuid7, hash_password
from app.db.database import SessionLocal
from app.models import Academy, Administrator
from app.schemas.registration import RegistrationRequest


class InvalidRegistrationPasswordError(Exception):
    pass


class RegistrationConflictError(Exception):
    pass


def register_academy(registration: RegistrationRequest) -> dict[str, dict[str, str]]:
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
        raise InvalidRegistrationPasswordError(
            "Password must include " + ", ".join(corrections)
        )

    academy = Academy(
        id=create_uuid7(),
        name=registration.academy_name,
        phone=registration.academy_phone,
    )
    administrator = Administrator(
        id=create_uuid7(),
        academy_id=academy.id,
        name=registration.administrator_name,
        email=registration.administrator_email,
        password_hash=hash_password(password),
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
        raise RegistrationConflictError(detail) from error

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
