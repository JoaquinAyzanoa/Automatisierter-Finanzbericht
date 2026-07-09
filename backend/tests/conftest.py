import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import create_app


@pytest.fixture
def tmp_env(monkeypatch) -> Generator[Path, None, None]:
    """Isolate reports dir per test."""
    with tempfile.TemporaryDirectory() as tmp:
        reports_dir = Path(tmp) / "reports"
        monkeypatch.setattr("app.core.config.settings.REPORTS_DIR", str(reports_dir))
        yield reports_dir


@pytest.fixture
def client(tmp_env) -> Generator[TestClient, None, None]:
    # In-memory SQLite shared across the connection pool for the test.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_connection, _):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    Base.metadata.drop_all(bind=engine)
