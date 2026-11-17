"""Real application routes backed only by temporary test databases and uploads."""

from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.auth import get_login_limiter
from app.api.registrations import get_registration_limiter
from app.core.config import Settings
from app.db.models import RateLimitBucket
from app.db.session import Base, get_db
from app.main import create_app
from app.services.rate_limits import LoginRateLimiter, RegistrationRateLimiter


@contextmanager
def isolated_api(frontend_port=5173, base_domain="localhost"):
    with TemporaryDirectory(prefix="blissbiz-frontend-test-") as directory:
        root = Path(directory)
        engine = create_engine(f"sqlite:///{root / 'application.sqlite'}")
        rate_engine = create_engine(f"sqlite:///{root / 'quotas.sqlite'}")
        Base.metadata.create_all(engine)
        RateLimitBucket.__table__.create(rate_engine)
        sessions = sessionmaker(bind=engine)
        rate_sessions = sessionmaker(bind=rate_engine)
        origin = f"http://admin.{base_domain}:{frontend_port}"
        config = Settings(
            _env_file=None,
            database_url="sqlite://",
            admin_base_url=origin,
            storefront_base_url=f"http://{base_domain}:{frontend_port}",
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
            yield app
        finally:
            engine.dispose()
            rate_engine.dispose()
