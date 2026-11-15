from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url.get_secret_value(),
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5},
)
SessionLocal = sessionmaker(bind=engine)

# Quota commits happen while a request holds its main DB connection. A separate
# bounded pool prevents nested checkouts from exhausting the main request pool.
rate_limit_engine = create_engine(
    settings.database_url.get_secret_value(),
    pool_pre_ping=True,
    pool_size=2,
    max_overflow=3,
    connect_args={"connect_timeout": 5},
)
RateLimitSessionLocal = sessionmaker(bind=rate_limit_engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
