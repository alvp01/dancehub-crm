from fastapi import APIRouter, Depends, Header, HTTPException

from app.core.security import verify_operator_secret
from app.db.availability import require_database_ready
from app.schemas.registration import RegistrationRequest
from app.services.registration_service import (
    InvalidRegistrationPasswordError,
    RegistrationConflictError,
    register_academy,
)

router = APIRouter(
    prefix="/operator",
    tags=["operator"],
    dependencies=[Depends(require_database_ready)],
)


@router.post("/registration", status_code=201)
def register_academy_endpoint(
    registration: RegistrationRequest,
    operator_secret: str | None = Header(default=None, alias="X-Operator-Secret"),
) -> dict[str, dict[str, str]]:
    if not verify_operator_secret(operator_secret):
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        return register_academy(registration)
    except InvalidRegistrationPasswordError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RegistrationConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
