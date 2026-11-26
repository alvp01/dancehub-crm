from fastapi import APIRouter, HTTPException

from app.db.availability import database_availability

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"message": "DanceHub CRM backend is running"}


@router.get("/ready")
def readiness() -> dict[str, str]:
    if not database_availability.ready:
        raise HTTPException(
            status_code=503,
            detail={"status": "degraded", "database": "unavailable"},
            headers={"Retry-After": "5"},
        )
    return {"status": "ready", "database": "available"}
