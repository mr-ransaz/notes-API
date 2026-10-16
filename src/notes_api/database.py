from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def create_database(url: str) -> tuple[Engine, sessionmaker[Session]]:
    engine = create_engine(url, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record) -> None:
        connection.execute("PRAGMA foreign_keys=ON")

    return engine, sessionmaker(engine, expire_on_commit=False)


def init_db(engine: Engine) -> None:
    # Import all models before metadata.create_all; this is not a migration system.
    from notes_api import models  # noqa: F401

    Base.metadata.create_all(engine)
