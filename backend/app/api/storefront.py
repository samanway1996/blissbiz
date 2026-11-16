from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.admin import PageNumber, PageSize, Search
from app.core.config import Settings, get_settings
from app.db.businesses import BusinessRepository
from app.db.models import Business
from app.db.products import ProductRepository
from app.db.session import get_db
from app.schemas.catalog import Page
from app.schemas.errors import ErrorResponse
from app.schemas.storefront import PublicProductResponse, StorefrontResponse
from app.services.storefront import StorefrontService

router = APIRouter(
    prefix="/storefront",
    tags=["public storefront"],
    responses={code: {"model": ErrorResponse} for code in (404, 422, 503)},
)


def get_storefront(
    db: Annotated[Session, Depends(get_db)], config: Annotated[Settings, Depends(get_settings)]
) -> StorefrontService:
    return StorefrontService(BusinessRepository(db), ProductRepository(db), config)


Storefront = Annotated[StorefrontService, Depends(get_storefront)]


def resolve_business(request: Request, response: Response, service: Storefront) -> Business:
    hosts = request.headers.getlist("host")
    if len(hosts) != 1:
        raise service.not_found()
    business = service.resolve(hosts[0])
    # No shared response cache: publication changes must be visible immediately.
    response.headers["Cache-Control"] = "no-store"
    response.headers["Vary"] = "Host"
    return business


Tenant = Annotated[Business, Depends(resolve_business)]


@router.get("", response_model=StorefrontResponse)
def profile(business: Tenant, service: Storefront):
    return service.profile(business)


@router.get("/products", response_model=Page[PublicProductResponse])
def products(
    business: Tenant,
    service: Storefront,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    q: Search | None = None,
):
    items, total = service.products.list(business.id, page, page_size, "published", q)
    return Page(
        items=[service.product_response(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/products/{product_id}", response_model=PublicProductResponse)
def product(product_id: str, business: Tenant, service: Storefront):
    record = service.products.find_published(business.id, product_id)
    if record is None:
        raise service.not_found()
    return service.product_response(record)
