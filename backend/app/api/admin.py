from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, UploadFile
from pydantic import StringConstraints
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.session_dependencies import require_owner_mutation, require_owner_session
from app.core.config import Settings, get_settings
from app.core.errors import ApiError
from app.db.businesses import BusinessRepository
from app.db.models import BrowserSession
from app.db.products import ProductRepository
from app.db.session import get_db
from app.schemas.catalog import (
    BusinessPatch,
    BusinessResponse,
    Page,
    ProductCreate,
    ProductPatch,
    ProductResponse,
    ProductStatus,
)
from app.schemas.errors import ErrorResponse
from app.services.business_urls import BusinessUrlBuilder
from app.services.catalog import CatalogService
from app.services.images import MAX_IMAGE_BYTES, CatalogMediaService, ImageStorage


def get_catalog(
    db: Annotated[Session, Depends(get_db)],
    config: Annotated[Settings, Depends(get_settings)],
) -> CatalogService:
    return CatalogService(BusinessRepository(db), ProductRepository(db), BusinessUrlBuilder(config))


def get_image_storage(config: Annotated[Settings, Depends(get_settings)]) -> ImageStorage:
    return ImageStorage(config.upload_dir)


def get_catalog_media(
    db: Annotated[Session, Depends(get_db)],
    catalog: Annotated[CatalogService, Depends(get_catalog)],
    storage: Annotated[ImageStorage, Depends(get_image_storage)],
) -> CatalogMediaService:
    return CatalogMediaService(db, catalog, storage)


Catalog = Annotated[CatalogService, Depends(get_catalog)]
Media = Annotated[CatalogMediaService, Depends(get_catalog_media)]
Owner = Annotated[BrowserSession, Depends(require_owner_session)]
Mutation = Annotated[BrowserSession, Depends(require_owner_mutation)]
Database = Annotated[Session, Depends(get_db)]
PageNumber = Annotated[int, Query(ge=1, le=1_000_000)]
PageSize = Annotated[int, Query(ge=1, le=100)]
Search = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]

router = APIRouter(
    prefix="/admin/businesses",
    tags=["owner catalog"],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 404, 413, 415, 422, 503)},
)


@router.get("", response_model=Page[BusinessResponse])
def list_businesses(
    response: Response,
    owner: Owner,
    catalog: Catalog,
    page: PageNumber = 1,
    page_size: PageSize = 20,
):
    items, total = catalog.businesses.list_owned(owner.owner_id, page, page_size)
    response.headers["Cache-Control"] = "no-store"
    return Page(
        items=[catalog.business_response(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{business_id}", response_model=BusinessResponse)
def get_business(business_id: str, response: Response, owner: Owner, catalog: Catalog):
    response.headers["Cache-Control"] = "no-store"
    return catalog.business_response(catalog.business(owner.owner_id, business_id))


def commit(db: Session) -> None:
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise


@router.patch("/{business_id}", response_model=BusinessResponse)
def update_business(
    business_id: str,
    data: BusinessPatch,
    response: Response,
    owner: Mutation,
    catalog: Catalog,
    db: Database,
):
    result = catalog.business_response(catalog.update_business(owner.owner_id, business_id, data))
    commit(db)
    response.headers["Cache-Control"] = "no-store"
    return result


@router.get("/{business_id}/products", response_model=Page[ProductResponse])
def list_products(
    business_id: str,
    response: Response,
    owner: Owner,
    catalog: Catalog,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    status: ProductStatus | None = None,
    q: Search | None = None,
):
    catalog.business(owner.owner_id, business_id)
    items, total = catalog.products.list(business_id, page, page_size, status, q)
    response.headers["Cache-Control"] = "no-store"
    return Page(
        items=[catalog.product_response(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("/{business_id}/products", response_model=ProductResponse, status_code=201)
def create_product(
    business_id: str,
    data: ProductCreate,
    response: Response,
    owner: Mutation,
    catalog: Catalog,
    db: Database,
):
    result = catalog.product_response(catalog.create_product(owner.owner_id, business_id, data))
    commit(db)
    response.headers["Cache-Control"] = "no-store"
    return result


@router.get("/{business_id}/products/{product_id}", response_model=ProductResponse)
def get_product(
    business_id: str, product_id: str, response: Response, owner: Owner, catalog: Catalog
):
    response.headers["Cache-Control"] = "no-store"
    return catalog.product_response(catalog.product(owner.owner_id, business_id, product_id))


@router.patch("/{business_id}/products/{product_id}", response_model=ProductResponse)
def update_product(
    business_id: str,
    product_id: str,
    data: ProductPatch,
    response: Response,
    owner: Mutation,
    catalog: Catalog,
    db: Database,
):
    result = catalog.product_response(
        catalog.update_product(owner.owner_id, business_id, product_id, data)
    )
    commit(db)
    response.headers["Cache-Control"] = "no-store"
    return result


@router.delete("/{business_id}/products/{product_id}", status_code=204)
def delete_product(business_id: str, product_id: str, owner: Mutation, media: Media):
    media.delete_product(owner.owner_id, business_id, product_id)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


def read_upload(file: UploadFile) -> bytes:
    data = file.file.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise ApiError(413, "image_too_large", "Images must not exceed 5 MiB.")
    return data


@router.put("/{business_id}/logo", response_model=BusinessResponse)
def upload_logo(
    business_id: str, file: UploadFile, response: Response, owner: Mutation, media: Media
):
    media.catalog.business(owner.owner_id, business_id)
    result = media.change(owner.owner_id, business_id, None, read_upload(file))
    response.headers["Cache-Control"] = "no-store"
    return result


@router.delete("/{business_id}/logo", status_code=204)
def remove_logo(business_id: str, owner: Mutation, media: Media):
    media.change(owner.owner_id, business_id, None, None)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.put("/{business_id}/products/{product_id}/image", response_model=ProductResponse)
def upload_product_image(
    business_id: str,
    product_id: str,
    file: UploadFile,
    response: Response,
    owner: Mutation,
    media: Media,
):
    media.catalog.product(owner.owner_id, business_id, product_id)
    result = media.change(owner.owner_id, business_id, product_id, read_upload(file))
    response.headers["Cache-Control"] = "no-store"
    return result


@router.delete("/{business_id}/products/{product_id}/image", status_code=204)
def remove_product_image(business_id: str, product_id: str, owner: Mutation, media: Media):
    media.change(owner.owner_id, business_id, product_id, None)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
