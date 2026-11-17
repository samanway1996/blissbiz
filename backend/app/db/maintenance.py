from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import BrowserSession, RateLimitBucket


class MaintenanceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def expired(self, now: datetime, *, apply: bool) -> dict[str, int]:
        counts = {}
        for model in (BrowserSession, RateLimitBucket):
            condition = model.expires_at <= now
            counts[model.__tablename__] = self.db.scalar(
                select(func.count()).select_from(model).where(condition)
            )
            if apply:
                self.db.execute(delete(model).where(condition))
        return counts
