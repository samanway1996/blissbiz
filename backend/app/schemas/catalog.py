import re
from datetime import datetime
from decimal import Decimal
from typing import Annotated, ClassVar, Generic, Literal, TypeVar

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    field_serializer,
    model_validator,
)

from app.schemas.registrations import BusinessUrls, Email, Name, Phone

Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)]
Address = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
ProductStatus = Literal["draft", "published"]


def validate_price(value: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9]{1,10}(?:\.[0-9]{1,2})?", value) is None:
        raise ValueError(
            "Use a nonnegative decimal string with at most 10 digits and 2 decimal places."
        )
    return value


Price = Annotated[
    Decimal, BeforeValidator(validate_price), Field(ge=0, max_digits=12, decimal_places=2)
]


class PatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    non_nullable: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def validate_changes(self):
        if not self.model_fields_set:
            raise ValueError("Supply at least one editable field.")
        if any(getattr(self, key) is None for key in self.model_fields_set & self.non_nullable):
            raise ValueError("Required fields cannot be null.")
        return self


class BusinessPatch(PatchRequest):
    non_nullable = frozenset({"name"})
    name: Name | None = None
    description: Description | None = None
    contact_email: Email | None = None
    contact_phone: Phone | None = None
    address: Address | None = None


class BusinessResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None
    contact_email: str | None
    contact_phone: str | None
    address: str | None
    currency: str
    logo_url: str | None
    urls: BusinessUrls
    created_at: datetime
    updated_at: datetime


class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name
    description: Description | None = None
    price: Price


class ProductPatch(PatchRequest):
    non_nullable = frozenset({"name", "price", "status"})
    name: Name | None = None
    description: Description | None = None
    price: Price | None = None
    status: ProductStatus | None = None


class ProductResponse(BaseModel):
    id: str
    business_id: str
    name: str
    description: str | None
    price: Decimal
    status: ProductStatus
    image_url: str | None
    created_at: datetime
    updated_at: datetime

    @field_serializer("price")
    def serialize_price(self, value: Decimal) -> str:
        return format(value, ".2f")


Item = TypeVar("Item")


class Page(BaseModel, Generic[Item]):
    items: list[Item]
    page: int
    page_size: int
    total: int
