import re
from urllib.parse import urlsplit

from app.core.config import Settings
from app.core.errors import ApiError
from app.core.slugs import SlugPolicy
from app.db.businesses import BusinessRepository
from app.db.models import Business, Product
from app.db.products import ProductRepository
from app.schemas.storefront import PublicProductResponse, StorefrontResponse


class StorefrontService:
    def __init__(
        self, businesses: BusinessRepository, products: ProductRepository, settings: Settings
    ) -> None:
        self.businesses = businesses
        self.products = products
        self.base_host = urlsplit(settings.storefront_base_url).hostname

    def resolve(self, host: str) -> Business:
        # Use the real Host preserved by our proxy. Forwarded tenant/host headers are ignored.
        if re.fullmatch(r"[A-Za-z0-9.-]+(?::[0-9]{1,5})?", host) is None:
            raise self.not_found()
        hostname, *ports = host.lower().split(":")
        if ports and not 1 <= int(ports[0]) <= 65535:
            raise self.not_found()
        suffix = f".{self.base_host}"
        if not hostname.endswith(suffix):
            raise self.not_found()
        slug = hostname[: -len(suffix)]
        try:
            if SlugPolicy.normalize(slug) != slug or SlugPolicy.is_reserved(slug):
                raise self.not_found()
        except ValueError:
            raise self.not_found() from None
        business = self.businesses.find_by_slug(slug)
        if business is None:
            raise self.not_found()
        return business

    @staticmethod
    def not_found() -> ApiError:
        return ApiError(404, "not_found", "Storefront or product not found.")

    @staticmethod
    def profile(business: Business) -> StorefrontResponse:
        return StorefrontResponse(
            name=business.name,
            slug=business.slug,
            description=business.description,
            contact_email=business.contact_email,
            contact_phone=business.contact_phone,
            address=business.address,
            currency=business.currency,
            logo_url=f"/media/{business.logo_path}" if business.logo_path else None,
        )

    @staticmethod
    def product_response(product: Product) -> PublicProductResponse:
        return PublicProductResponse(
            id=product.id,
            name=product.name,
            description=product.description,
            price=product.price,
            image_url=f"/media/{product.image_path}" if product.image_path else None,
        )
