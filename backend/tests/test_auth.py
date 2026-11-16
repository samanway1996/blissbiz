from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.api.auth import get_login_limiter
from app.api.session_dependencies import get_session_service
from app.core.config import Settings, get_settings
from app.core.errors import ApiError
from app.core.passwords import PasswordService
from app.db.models import Owner, RateLimitBucket, utc_now
from app.db.session import get_db
from app.db.sessions import SessionRepository
from app.main import app
from app.services.rate_limits import LoginRateLimiter
from app.services.sessions import SessionService


@pytest.fixture
def auth_context(db, tmp_path, monkeypatch):
    settings = Settings(
        _env_file=None, database_url="sqlite://", auth_allowed_origins=["http://testserver"]
    )
    engine = create_engine(f"sqlite:///{tmp_path / 'login-limits.sqlite'}")
    RateLimitBucket.__table__.create(engine)
    limiter = LoginRateLimiter(sessionmaker(bind=engine), settings, clock=lambda: 1800.0)
    sessions = SessionService(SessionRepository(db), settings)
    for dependency, provider in {
        get_db: lambda: db,
        get_settings: lambda: settings,
        get_session_service: lambda: sessions,
        get_login_limiter: lambda: limiter,
    }.items():
        monkeypatch.setitem(app.dependency_overrides, dependency, provider)
    with TestClient(app) as client:
        yield client, sessions, settings, limiter
    engine.dispose()


@pytest.fixture
def login_owner(db):
    owner = Owner(
        full_name="Owner One",
        email=f"{uuid4().hex}@example.com",
        password_hash=PasswordService().hash("a long test passphrase"),
        phone="private",
    )
    db.add(owner)
    db.flush()
    return owner


def headers(client):
    token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    return {"Origin": "http://testserver", "X-CSRF-Token": token}


def sign_in(client, owner):
    return client.post(
        "/api/v1/auth/login",
        headers=headers(client),
        json={"email": owner.email.upper(), "password": "a long test passphrase"},
    )


def test_login_me_logout_and_replay(auth_context, login_owner):
    client, sessions, settings, _ = auth_context
    old_headers = headers(client)
    old_cookie = client.cookies.get(settings.session_cookie_name)
    response = sign_in(client, login_owner)
    assert response.status_code == 200
    assert response.json() == {
        "id": login_owner.id,
        "full_name": "Owner One",
        "email": login_owner.email,
    }
    cookie = client.cookies.get(settings.session_cookie_name)
    assert cookie != old_cookie and sessions.current(old_cookie) is None
    assert sessions.require_owner(cookie).owner_id == login_owner.id
    assert response.headers["cache-control"] == "no-store"
    profile = client.get("/api/v1/auth/me")
    assert profile.json() == response.json() and profile.headers["cache-control"] == "no-store"
    assert client.post("/api/v1/auth/logout", headers=old_headers).status_code == 403
    fresh_headers = headers(client)
    assert fresh_headers != old_headers
    response = client.post("/api/v1/auth/logout", headers=fresh_headers)
    assert response.status_code == 204 and response.content == b""
    assert "Max-Age=0" in response.headers["set-cookie"]
    assert sessions.current(cookie) is None
    client.cookies.set(settings.session_cookie_name, cookie)
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.post("/api/v1/auth/logout", headers=fresh_headers).status_code == 401


def test_profiles_follow_cookie_owner(auth_context, login_owner, db):
    client, sessions, settings, _ = auth_context
    other = Owner(full_name="Owner Two", email=f"{uuid4().hex}@example.com", password_hash="unused")
    db.add(other)
    db.flush()
    credentials = sessions.bootstrap(None)
    credentials = sessions.rotate(credentials.raw_token, other.id)
    db.commit()
    client.cookies.set(settings.session_cookie_name, credentials.raw_token)
    response = client.get("/api/v1/auth/me", params={"owner_id": login_owner.id})
    assert response.status_code == 200 and response.json()["id"] == other.id


@pytest.mark.parametrize("state", ["missing", "anonymous", "expired", "malformed"])
def test_me_rejects_invalid_sessions(auth_context, login_owner, db, state):
    client, sessions, settings, _ = auth_context
    if state == "malformed":
        client.cookies.set(settings.session_cookie_name, "bad")
    elif state in {"anonymous", "expired"}:
        headers(client)
        if state == "expired":
            credentials = sessions.rotate(
                client.cookies.get(settings.session_cookie_name), login_owner.id
            )
            credentials.record.expires_at = utc_now() - timedelta(seconds=1)
            db.commit()
            client.cookies.clear()
            client.cookies.set(settings.session_cookie_name, credentials.raw_token)
    assert client.get("/api/v1/auth/me").status_code == 401


def test_unknown_and_wrong_password_have_identical_errors(auth_context, login_owner):
    client, sessions, settings, _ = auth_context
    csrf = headers(client)
    cookie = client.cookies.get(settings.session_cookie_name)
    results = [
        client.post("/api/v1/auth/login", headers=csrf, json={"email": email, "password": "wrong"})
        for email in [login_owner.email, "missing@example.com"]
    ]
    assert all(r.status_code == 401 and "set-cookie" not in r.headers for r in results)
    assert results[0].json() == results[1].json()
    assert sessions.current(cookie).owner_id is None


@pytest.mark.parametrize("mode", ["csrf", "origin", "cookie"])
def test_mutations_reject_unverified_requests(auth_context, login_owner, mode):
    client, _, _, _ = auth_context
    csrf = headers(client)
    if mode == "csrf":
        csrf["X-CSRF-Token"] = "x" * 43
    elif mode == "origin":
        csrf["Origin"] = "https://evil.example.com"
    else:
        client.cookies.clear()
    assert (
        client.post(
            "/api/v1/auth/login",
            headers=csrf,
            json={"email": login_owner.email, "password": "a long test passphrase"},
        ).status_code
        == 403
    )
    sign_in(client, login_owner)
    csrf = headers(client)
    if mode == "csrf":
        csrf.pop("X-CSRF-Token")
    elif mode == "origin":
        csrf["Origin"] = "https://evil.example.com"
    else:
        client.cookies.clear()
    assert client.post("/api/v1/auth/logout", headers=csrf).status_code == (
        401 if mode == "cookie" else 403
    )


@pytest.mark.parametrize("operation", ["login", "logout"])
def test_commit_failure_preserves_old_session(
    auth_context, login_owner, db, monkeypatch, operation
):
    client, sessions, settings, _ = auth_context
    if operation == "logout":
        assert sign_in(client, login_owner).status_code == 200
    csrf = headers(client)
    cookie = client.cookies.get(settings.session_cookie_name)

    def fail():
        raise OperationalError("private SQL", {}, Exception("secret"))

    monkeypatch.setattr(db, "commit", fail)
    body = (
        {"email": login_owner.email, "password": "a long test passphrase"}
        if operation == "login"
        else None
    )
    response = client.post(f"/api/v1/auth/{operation}", headers=csrf, json=body)
    assert response.status_code == 503 and "set-cookie" not in response.headers
    assert "secret" not in response.text and sessions.current(cookie) is not None


@pytest.mark.parametrize("scope", ["peer", "account"])
def test_login_limits_failures_and_window_reset(auth_context, login_owner, scope):
    client, _, settings, limiter = auth_context
    setattr(settings, f"login_{scope}_rate_limit", 1)
    csrf = headers(client)
    payload = {"email": login_owner.email, "password": "wrong"}
    assert client.post("/api/v1/auth/login", headers=csrf, json=payload).status_code == 401
    if scope == "peer":
        payload["email"] = "different@example.com"
    else:
        payload["email"] = login_owner.email.upper()
    response = client.post(
        "/api/v1/auth/login", headers={**csrf, "X-Forwarded-For": "new-peer"}, json=payload
    )
    assert response.status_code == 429 and response.headers["retry-after"] == "900"
    if scope == "account":
        with pytest.raises(ApiError) as error:
            limiter.enforce_login("different-peer", login_owner.email)
        assert error.value.status_code == 429
    limiter.clock = lambda: 2700.0
    assert client.post("/api/v1/auth/login", headers=csrf, json=payload).status_code == 401
    with limiter.session_factory() as session:
        assert all(
            login_owner.email not in row.key_hash
            for row in session.scalars(select(RateLimitBucket))
        )


def test_successful_login_consumes_quota(auth_context, login_owner):
    client, sessions, settings, _ = auth_context
    settings.login_account_rate_limit = 1
    assert sign_in(client, login_owner).status_code == 200
    cookie = client.cookies.get(settings.session_cookie_name)
    response = sign_in(client, login_owner)
    assert response.status_code == 429 and "set-cookie" not in response.headers
    assert sessions.require_owner(cookie).owner_id == login_owner.id


@pytest.mark.parametrize(
    "body",
    [
        {"email": "bad", "password": "wrong"},
        {"email": "test@example.com", "password": "x" * 129},
        {"email": "test@example.com", "password": "wrong", "owner_id": "injected"},
    ],
)
def test_login_validation_is_safe(auth_context, body):
    client, _, _, _ = auth_context
    response = client.post("/api/v1/auth/login", headers=headers(client), json=body)
    assert response.status_code == 422 and "wrong" not in response.text
