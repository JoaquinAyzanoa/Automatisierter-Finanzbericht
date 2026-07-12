from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# SQLite-specific: allow the connection to be shared across threads
# (FastAPI runs endpoints in a threadpool). Safe because each request
# gets its own Session via the get_db dependency.
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=settings.DEBUG,
)


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Enforce foreign keys and enable WAL for better concurrent reads."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    """Create tables. For real migrations, switch to Alembic (batch mode)."""
    from app.db.base import Base

    # Import models so they are registered on Base.metadata before create_all.
    import app.models.operacion  # noqa: F401
    import app.models.report  # noqa: F401
    import app.models.user  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    return SessionLocal()
