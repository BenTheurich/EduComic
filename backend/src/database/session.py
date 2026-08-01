"""Local SQLAlchemy engine and session setup."""

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import sessionmaker


def create_local_engine(database_url: str) -> Engine:
    engine = create_engine(database_url)
    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_session_factory(database_url: str) -> sessionmaker:
    return sessionmaker(bind=create_local_engine(database_url), expire_on_commit=False)
