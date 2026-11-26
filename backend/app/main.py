import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import InterfaceError, OperationalError, TimeoutError

from app.core.config import get_settings
from app.db.availability import database_availability
from app.db.database import engine
from app.db.lifecycle import monitor_database
from app.routers.api import router as api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    database_availability.ready = False
    database_monitor = asyncio.create_task(monitor_database())
    try:
        yield
    finally:
        database_monitor.cancel()
        with suppress(asyncio.CancelledError):
            await database_monitor
        database_availability.ready = False
        await asyncio.to_thread(engine.dispose)


app = FastAPI(title="DanceHub CRM API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api/v1")


async def database_unavailable_handler(
    _: Request, error: OperationalError | InterfaceError | TimeoutError
) -> JSONResponse:
    database_availability.ready = False
    logger.warning(
        "Database operation failed; marking service as degraded: %s", error
    )
    return JSONResponse(
        status_code=503,
        content={"detail": "Database is temporarily unavailable."},
        headers={"Retry-After": "5"},
    )


app.add_exception_handler(OperationalError, database_unavailable_handler)
app.add_exception_handler(InterfaceError, database_unavailable_handler)
app.add_exception_handler(TimeoutError, database_unavailable_handler)
