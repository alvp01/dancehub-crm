from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.core.security import ACCESS_TOKEN_LIFETIME_SECONDS
from app.db.availability import require_database_ready
from app.schemas.auth import AdministratorSession, LoginRequest
from app.services.auth_service import (
    InvalidAccessTokenError,
    InvalidCredentialsError,
    InvalidRefreshSessionError,
    authenticate_administrator,
    get_administrator_session,
    revoke_refresh_session,
    rotate_refresh_session,
)

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    dependencies=[Depends(require_database_ready)],
)
REFRESH_SESSION_LIFETIME_SECONDS = 7 * 24 * 60 * 60


def set_auth_cookies(
    request: Request,
    response: Response,
    access_token: str,
    refresh_token: str,
) -> None:
    secure = request.url.scheme == "https"
    response.set_cookie(
        key="dancehub_access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=secure,
        max_age=ACCESS_TOKEN_LIFETIME_SECONDS,
        path="/api/v1",
    )
    response.set_cookie(
        key="dancehub_refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=secure,
        max_age=REFRESH_SESSION_LIFETIME_SECONDS,
        path="/api/v1/auth",
    )


@router.post("/login")
def login(
    credentials: LoginRequest, request: Request, response: Response
) -> dict[str, str]:
    try:
        access_token, refresh_token = authenticate_administrator(
            credentials.email, credentials.password
        )
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=401,
            detail="Email or password is incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
    set_auth_cookies(request, response, access_token, refresh_token)
    return {"message": "Signed in."}


@router.post("/refresh")
def refresh_session(request: Request, response: Response) -> dict[str, str]:
    refresh_token = request.cookies.get("dancehub_refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh session is invalid.")
    try:
        access_token, new_refresh_token = rotate_refresh_session(refresh_token)
    except InvalidRefreshSessionError as error:
        raise HTTPException(
            status_code=401, detail="Refresh session is invalid."
        ) from error
    set_auth_cookies(request, response, access_token, new_refresh_token)
    return {"message": "Session renewed."}


@router.post("/logout")
def logout(request: Request, response: Response) -> dict[str, str]:
    revoke_refresh_session(request.cookies.get("dancehub_refresh_token"))
    secure = request.url.scheme == "https"
    response.delete_cookie(
        key="dancehub_access_token",
        path="/api/v1",
        httponly=True,
        samesite="lax",
        secure=secure,
    )
    response.delete_cookie(
        key="dancehub_refresh_token",
        path="/api/v1/auth",
        httponly=True,
        samesite="lax",
        secure=secure,
    )
    return {"message": "Signed out."}


@router.get("/me", response_model=AdministratorSession)
def get_current_administrator(request: Request) -> AdministratorSession:
    access_token = request.cookies.get("dancehub_access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="Sign-in required.")
    try:
        administrator = get_administrator_session(access_token)
    except InvalidAccessTokenError as error:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
    return AdministratorSession(**administrator)
