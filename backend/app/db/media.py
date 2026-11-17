from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Business, Product


class MediaRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def is_referenced(self, path: str) -> bool:
        return (
            self.session.scalar(select(Business.id).where(Business.logo_path == path).limit(1))
            is not None
            or self.session.scalar(select(Product.id).where(Product.image_path == path).limit(1))
            is not None
        )
