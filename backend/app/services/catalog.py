from app.core.errors import ApiError
from app.db.businesses import BusinessRepository
from app.db.models import Business, Product
from app.db.products import ProductRepository
from app.schemas.catalog import (
    BusinessPatch,
    BusinessResponse,
    ProductCreate,
    ProductPatch,
    ProductResponse,
)
from app.services.business_urls import BusinessUrlBuilder


class CatalogService:
    def __init__(
        self, businesses: BusinessRepository, products: ProductRepository, urls: BusinessUrlBuilder
    ) -> None:
        self.businesses = businesses
        self.products = products
        self.urls = urls

    def business(self, owner_id: str, business_id: str, *, lock: bool = False) -> Business:
        business = self.businesses.owned(owner_id, business_id, lock=lock)
        if business is None:
            raise ApiError(404, "not_found", "Business not found.")
        return business

    def product(
        self, owner_id: str, business_id: str, product_id: str, *, lock: bool = False
    ) -> Product:
        self.business(owner_id, business_id, lock=lock)
        product = self.products.find(business_id, product_id, lock=lock)
        if product is None:
            raise ApiError(404, "not_found", "Product not found.")
        return product

    def update_business(self, owner_id: str, business_id: str, data: BusinessPatch) -> Business:
        business = self.business(owner_id, business_id, lock=True)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(business, key, value)
        self.businesses.session.flush()
        self.businesses.session.refresh(business, with_for_update=True)
        return business

    def create_product(self, owner_id: str, business_id: str, data: ProductCreate) -> Product:
        self.business(owner_id, business_id, lock=True)
        product = Product(business_id=business_id, **data.model_dump())
        self.products.add(product)
        return product

    def update_product(
        self, owner_id: str, business_id: str, product_id: str, data: ProductPatch
    ) -> Product:
        product = self.product(owner_id, business_id, product_id, lock=True)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(product, key, value)
        self.products.session.flush()
        self.products.session.refresh(product, with_for_update=True)
        return product

    def business_response(self, business: Business) -> BusinessResponse:
        return BusinessResponse(
            **{
                key: getattr(business, key)
                for key in (
                    "id",
                    "name",
                    "slug",
                    "description",
                    "contact_email",
                    "contact_phone",
                    "address",
                    "currency",
                    "created_at",
                    "updated_at",
                )
            },
            logo_url=self.media_url(business.logo_path),
            urls=self.urls.for_slug(business.slug),
        )

    def product_response(self, product: Product) -> ProductResponse:
        return ProductResponse(
            **{
                key: getattr(product, key)
                for key in (
                    "id",
                    "business_id",
                    "name",
                    "description",
                    "price",
                    "status",
                    "created_at",
                    "updated_at",
                )
            },
            image_url=self.media_url(product.image_path),
        )

    @staticmethod
    def media_url(path: str | None) -> str | None:
        return f"/media/{path}" if path else None
