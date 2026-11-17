from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Owner


class OwnerRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def email_exists(self, email: str) -> bool:
        return (
            self.session.scalar(select(Owner.id).where(Owner.email == email).limit(1)) is not None
        )

    def find_by_email(self, email: str) -> Owner | None:
        return self.session.scalar(select(Owner).where(Owner.email == email))

    def find_by_id(self, owner_id: str) -> Owner | None:
        return self.session.get(Owner, owner_id)

    def add(self, owner: Owner) -> None:
        self.session.add(owner)
        self.session.flush()
