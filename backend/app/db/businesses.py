from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Business


class BusinessRepository:
    """Database operations; callers own transaction boundaries."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def slug_exists(self, slug: str) -> bool:
        statement = select(Business.id).where(Business.slug == slug).limit(1)
        return self.session.scalar(statement) is not None

    def owned(self, owner_id: str, business_id: str, *, lock: bool = False) -> Business | None:
        statement = select(Business).where(
            Business.id == business_id, Business.owner_id == owner_id
        )
        if lock:
            statement = statement.with_for_update().execution_options(populate_existing=True)
        return self.session.scalar(statement)

    def list_owned(self, owner_id: str, page: int, page_size: int) -> tuple[list[Business], int]:
        from sqlalchemy import func

        condition = Business.owner_id == owner_id
        total = self.session.scalar(select(func.count()).select_from(Business).where(condition))
        items = self.session.scalars(
            select(Business)
            .where(condition)
            .order_by(Business.created_at.desc(), Business.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return list(items), total

    def add(self, business: Business) -> None:
        self.session.add(business)
        self.session.flush()
