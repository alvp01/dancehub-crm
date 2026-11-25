import os
import subprocess
import time

from sqlalchemy import create_engine, text


def wait_for_database() -> None:
    engine = create_engine(os.environ["DATABASE_URL"])
    for attempt in range(30):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except Exception as error:
            if attempt == 29:
                raise
            print(f"Waiting for database ({attempt + 1}/30): {error}", flush=True)
            time.sleep(2)


if __name__ == "__main__":
    wait_for_database()
    subprocess.run(["alembic", "upgrade", "head"], check=True)
    subprocess.run(
        ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        check=True,
    )
