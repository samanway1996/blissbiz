"""Run the real FastAPI routes with disposable SQLite stores; never use the local DB."""

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.auth import get_login_limiter
from app.api.registrations import get_registration_limiter
from app.core.config import Settings
from app.db.models import RateLimitBucket
from app.db.session import Base, get_db
from app.main import create_app
from app.services.rate_limits import LoginRateLimiter, RegistrationRateLimiter


def main():
    with TemporaryDirectory(prefix="blissbiz-frontend-api-") as directory:
        root = Path(directory)
        engine = create_engine(f"sqlite:///{root / 'application.sqlite'}")
        rate_engine = create_engine(f"sqlite:///{root / 'quotas.sqlite'}")
        Base.metadata.create_all(engine)
        RateLimitBucket.__table__.create(rate_engine)
        sessions = sessionmaker(bind=engine)
        rate_sessions = sessionmaker(bind=rate_engine)
        origin = "http://admin.localhost:5173"
        config = Settings(
            _env_file=None,
            database_url="sqlite://",
            admin_base_url=origin,
            storefront_base_url="http://localhost:5173",
            auth_allowed_origins=[origin],
            upload_dir=root / "uploads",
        )
        app = create_app(config)

        def database():
            with sessions() as session:
                yield session

        app.dependency_overrides[get_db] = database
        app.dependency_overrides[get_login_limiter] = lambda: LoginRateLimiter(
            rate_sessions, config
        )
        app.dependency_overrides[get_registration_limiter] = lambda: RegistrationRateLimiter(
            rate_sessions, config
        )
        try:
            with TestClient(app, base_url=origin) as client:
                for line in sys.stdin:
                    request = json.loads(line)
                    assert request["url"].startswith("/api/")
                    response = client.request(
                        request["method"],
                        request["url"],
                        content=request.get("body"),
                        headers={**request["headers"], "Origin": origin},
                    )
                    print(
                        json.dumps(
                            {
                                "status": response.status_code,
                                "body": response.text,
                                "headers": {
                                    "Content-Type": response.headers.get("Content-Type", ""),
                                    "Retry-After": response.headers.get("Retry-After", ""),
                                },
                            }
                        ),
                        flush=True,
                    )
        finally:
            engine.dispose()
            rate_engine.dispose()


if __name__ == "__main__":
    main()
