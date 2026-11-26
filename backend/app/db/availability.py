from fastapi import HTTPException


class DatabaseAvailability:
    def __init__(self) -> None:
        self.ready = False


database_availability = DatabaseAvailability()


def require_database_ready() -> None:
    if not database_availability.ready:
        raise HTTPException(
            status_code=503,
            detail="Database is temporarily unavailable.",
            headers={"Retry-After": "5"},
        )
