import asyncio
import logging
import random
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.core.config import get_settings
from app.db.availability import database_availability
from app.db.database import engine

logger = logging.getLogger(__name__)
_ALEMBIC_CONFIG_PATH = Path(__file__).resolve().parents[2] / "alembic.ini"


def check_database_connection() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def apply_database_migrations() -> None:
    command.upgrade(Config(str(_ALEMBIC_CONFIG_PATH)), "head")


async def monitor_database() -> None:
    settings = get_settings()
    retry_delay = min(
        settings.database_retry_initial_seconds,
        settings.database_retry_max_seconds,
    )
    migrations_required = True

    while True:
        try:
            await asyncio.to_thread(check_database_connection)
            if migrations_required:
                await asyncio.to_thread(apply_database_migrations)
                await asyncio.to_thread(check_database_connection)
        except Exception:
            database_availability.ready = False
            logger.warning(
                "Database unavailable; retrying in %.1f seconds.",
                retry_delay,
                exc_info=True,
            )
            await asyncio.to_thread(engine.dispose)
            await asyncio.sleep(
                min(
                    retry_delay * random.uniform(0.8, 1.2),
                    settings.database_retry_max_seconds,
                )
            )
            retry_delay = min(
                retry_delay * 2, settings.database_retry_max_seconds
            )
            migrations_required = True
            continue

        was_ready = database_availability.ready
        database_availability.ready = True
        if not was_ready:
            logger.info("Database is ready.")
        retry_delay = min(
            settings.database_retry_initial_seconds,
            settings.database_retry_max_seconds,
        )
        migrations_required = False
        await asyncio.sleep(settings.database_health_check_interval_seconds)
