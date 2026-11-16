from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.models import Product


class ProductRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def find(self, business_id: str, product_id: str, *, lock: bool = False) -> Product | None:
        statement = (
            select(Product)
            .where(Product.business_id == business_id, Product.id == product_id)
            .execution_options(populate_existing=True)
        )
        if lock:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def list(
        self, business_id: str, page: int, page_size: int, status: str | None, query: str | None
    ) -> tuple[list[Product], int]:
        conditions = [Product.business_id == business_id]
        if status is not None:
            conditions.append(Product.status == status)
        if query is not None:
            conditions.append(
                or_(
                    Product.name.icontains(query, autoescape=True),
                    Product.description.icontains(query, autoescape=True),
                )
            )
        total = self.session.scalar(select(func.count()).select_from(Product).where(*conditions))
        items = self.session.scalars(
            select(Product)
            .where(*conditions)
            .order_by(Product.created_at.desc(), Product.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return list(items), total

    def add(self, product: Product) -> None:
        self.session.add(product)
        self.session.flush()
        self.session.refresh(product)

    def remove(self, product: Product) -> None:
        self.session.delete(product)
        self.session.flush()
