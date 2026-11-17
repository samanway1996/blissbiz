import hashlib
import math
import time
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import ApiError
from app.db.rate_limits import RateLimitRepository


class FixedWindowRateLimiter:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        settings: Settings,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.clock = clock

    def consume(self, key: str, end: int, limit: int, action: str) -> None:
        with self.session_factory() as session, session.begin():
            allowed = RateLimitRepository(session).consume(
                key,
                datetime.fromtimestamp(end, UTC).replace(tzinfo=None),
                limit,
            )
        # Keep quota consumption committed even when the request fails or is rejected.
        if not allowed:
            retry_after = max(1, math.ceil(end - self.clock()))
            raise ApiError(
                429,
                "rate_limited",
                f"Too many {action} attempts. Try again later.",
                headers={"Retry-After": str(retry_after)},
            )


class RegistrationRateLimiter(FixedWindowRateLimiter):
    def bucket(self, peer: str) -> tuple[str, int]:
        window = self.settings.registration_rate_window_seconds
        start = int(self.clock()) // window * window
        key = hashlib.sha256(f"registration:{peer}:{start}".encode()).hexdigest()
        return key, start + window

    def enforce(self, peer: str) -> None:
        key, end = self.bucket(peer)
        self.consume(key, end, self.settings.registration_rate_limit, "registration")


class LoginRateLimiter(FixedWindowRateLimiter):
    def enforce_login(self, peer: str, email: str) -> None:
        window = self.settings.login_rate_window_seconds
        start = int(self.clock()) // window * window
        for scope, identity, limit in (
            ("peer", peer, self.settings.login_peer_rate_limit),
            ("account", email, self.settings.login_account_rate_limit),
        ):
            key = hashlib.sha256(f"login:{scope}:{identity}:{start}".encode()).hexdigest()
            self.consume(key, start + window, limit, "login")
