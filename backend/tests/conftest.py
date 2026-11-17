import os
from collections.abc import Iterator
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.models import Business, Owner
from app.db.session import Base, engine, get_db
from app.main import app

DATABASES = ["sqlite"] + (["mysql"] if os.getenv("BLISSBIZ_TEST_MYSQL") == "1" else [])


@pytest.fixture(params=DATABASES)
def db(request) -> Iterator[Session]:
    """Use real SQL on both engines; test writes are never committed."""
    test_engine = engine
    if request.param == "sqlite":
        test_engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(test_engine, "connect")
        def enable_foreign_keys(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(test_engine)

    with test_engine.connect() as connection:
        transaction = connection.begin()
        try:
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                yield session
        finally:
            if transaction.is_active:
                transaction.rollback()
    if request.param == "sqlite":
        test_engine.dispose()


@pytest.fixture
def api_client(db, monkeypatch) -> Iterator[TestClient]:
    monkeypatch.setitem(app.dependency_overrides, get_db, lambda: db)
    with TestClient(app) as client:
        yield client


@pytest.fixture
def existing_business(db) -> Business:
    unique = uuid4().hex
    owner = Owner(
        full_name="Test Owner",
        email=f"{unique}@example.com",
        password_hash="test-placeholder-not-a-real-password-hash",
    )
    db.add(owner)
    db.flush()
    business = Business(owner_id=owner.id, name="Test Bakery", slug=f"taken-{unique}")
    db.add(business)
    db.flush()
    return business


@pytest.fixture
def catalog_context(db, existing_business, tmp_path, monkeypatch):
    from app.api.session_dependencies import get_session_service
    from app.core.config import Settings, get_settings
    from app.db.sessions import SessionRepository
    from app.services.sessions import SessionService

    sibling = Business(
        owner_id=existing_business.owner_id, name="Second Shop", slug=f"second-{uuid4().hex}"
    )
    other_owner = Owner(
        full_name="Other Owner", email=f"{uuid4().hex}@example.com", password_hash="private"
    )
    db.add_all([sibling, other_owner])
    db.flush()
    foreign = Business(owner_id=other_owner.id, name="Other Shop", slug=f"foreign-{uuid4().hex}")
    db.add(foreign)
    db.flush()
    config = Settings(
        _env_file=None,
        database_url="sqlite://",
        upload_dir=tmp_path / "uploads",
        auth_allowed_origins=["http://testserver"],
    )
    service = SessionService(SessionRepository(db), config)
    credentials = service.bootstrap(None)
    credentials = service.rotate(credentials.raw_token, existing_business.owner_id)
    csrf = credentials.record.csrf_token
    db.commit()
    for dependency, provider in {
        get_db: lambda: db,
        get_settings: lambda: config,
        get_session_service: lambda: service,
    }.items():
        monkeypatch.setitem(app.dependency_overrides, dependency, provider)
    with TestClient(app) as client:
        client.cookies.set(config.session_cookie_name, credentials.raw_token)
        yield SimpleNamespace(
            client=client,
            business=existing_business,
            sibling=sibling,
            foreign=foreign,
            settings=config,
            headers={"Origin": "http://testserver", "X-CSRF-Token": csrf},
            base=f"/api/v1/admin/businesses/{existing_business.id}",
            db=db,
        )
