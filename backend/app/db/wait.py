import logging
import os
import time

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.settings.config import Settings

logger = logging.getLogger("database-wait")


def wait_for_database() -> None:
    settings = Settings()
    max_attempts = int(os.getenv("DB_CONNECT_MAX_ATTEMPTS", "12"))
    retry_seconds = float(os.getenv("DB_CONNECT_RETRY_SECONDS", "5"))
    engine = create_engine(
        settings.sqlalchemy_url(),
        pool_pre_ping=True,
        connect_args={"connect_timeout": 10} if settings.database_backend == "mysql" else {},
    )

    try:
        for attempt in range(1, max_attempts + 1):
            try:
                with engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
                logger.info(
                    "Database connection is ready (engine=%s, attempt=%s)",
                    settings.database_backend,
                    attempt,
                )
                return
            except SQLAlchemyError as exc:
                if attempt == max_attempts:
                    raise RuntimeError(
                        f"Database was not ready after {max_attempts} attempts "
                        f"(engine={settings.database_backend})"
                    ) from exc
                logger.warning(
                    "Database is not ready (engine=%s, attempt=%s/%s); retrying in %ss",
                    settings.database_backend,
                    attempt,
                    max_attempts,
                    retry_seconds,
                )
                time.sleep(retry_seconds)
    finally:
        engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    wait_for_database()
