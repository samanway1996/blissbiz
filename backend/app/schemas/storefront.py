from decimal import Decimal

from pydantic import BaseModel, field_serializer


class StorefrontResponse(BaseModel):
    name: str
    slug: str
    description: str | None
    contact_email: str | None
    contact_phone: str | None
    address: str | None
    currency: str
    logo_url: str | None


class PublicProductResponse(BaseModel):
    id: str
    name: str
    description: str | None
    price: Decimal
    image_url: str | None

    @field_serializer("price")
    def serialize_price(self, value: Decimal) -> str:
        return format(value, ".2f")
