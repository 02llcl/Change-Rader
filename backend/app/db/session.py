from collections.abc import Generator

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker


class Database:
    def __init__(self, url: str | URL) -> None:
        parsed_url = make_url(url)
        backend = parsed_url.get_backend_name()
        connect_args: dict[str, object] = {}
        engine_options: dict[str, object] = {"pool_pre_ping": True}

        if backend == "sqlite":
            connect_args["check_same_thread"] = False
        elif backend == "mysql":
            connect_args.update({"connect_timeout": 10, "charset": "utf8mb4"})
            engine_options.update({"pool_size": 5, "max_overflow": 5, "pool_recycle": 280})

        self.backend = backend
        self.engine = create_engine(
            parsed_url,
            connect_args=connect_args,
            **engine_options,
        )
        self.session_factory = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)

    def create_all(self) -> None:
        from app.db.models import Base

        Base.metadata.create_all(self.engine)

    def dispose(self) -> None:
        self.engine.dispose()


def get_db(request: Request) -> Generator[Session, None, None]:
    session = request.app.state.database.session_factory()
    try:
        yield session
    finally:
        session.close()
