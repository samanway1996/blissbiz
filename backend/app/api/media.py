from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.api.admin import get_catalog_media
from app.core.errors import ApiError
from app.services.images import CatalogMediaService

router = APIRouter(tags=["public images"])


@router.get("/media/{path:path}", response_class=FileResponse)
def get_image(path: str, service: Annotated[CatalogMediaService, Depends(get_catalog_media)]):
    target = service.storage.resolve(path)
    if not target.is_file() or not service.images.is_referenced(path):
        raise ApiError(404, "not_found", "Image not found.")
    return FileResponse(
        target,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "public, max-age=3600"},
    )
