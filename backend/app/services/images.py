import io
import logging
import re
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.db.media import MediaRepository
from app.schemas.catalog import BusinessResponse, ProductResponse
from app.services.catalog import CatalogService

logger = logging.getLogger(__name__)
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
UUID_PATTERN = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
IMAGE_PATH = re.compile(rf"businesses/{UUID_PATTERN}/[0-9a-f]{{32}}\.(?:jpg|png|webp)")


class ImageStorage:
    """Only generated image paths are accepted; original filenames are never used."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def resolve(self, path: str) -> Path:
        if IMAGE_PATH.fullmatch(path) is None:
            raise ApiError(404, "not_found", "Image not found.")
        target = self.root / path
        if not target.resolve().is_relative_to(self.root) or any(
            parent.is_symlink() for parent in (target, *target.parents) if parent != self.root
        ):
            raise ApiError(404, "not_found", "Image not found.")
        return target

    def save(self, business_id: str, data: bytes) -> str:
        if len(data) > MAX_IMAGE_BYTES:
            raise ApiError(413, "image_too_large", "Images must not exceed 5 MiB.")
        try:
            with Image.open(io.BytesIO(data), formats=["JPEG", "PNG", "WEBP"]) as image:
                if (
                    image.width * image.height > MAX_IMAGE_PIXELS
                    or getattr(image, "n_frames", 1) != 1
                ):
                    raise ApiError(
                        422, "invalid_image", "Use a still image of at most 20 megapixels."
                    )
                image_format = image.format
                image.verify()
            with Image.open(io.BytesIO(data), formats=["JPEG", "PNG", "WEBP"]) as image:
                image.load()
                ImageOps.exif_transpose(image, in_place=True)
                # Re-encode pixels only; discard metadata and trailing/polyglot content.
                alpha = "A" in image.getbands() or "transparency" in image.info
                mode = "RGBA" if image_format != "JPEG" and alpha else "RGB"
                clean = Image.new(mode, image.size)
                clean.paste(image.convert(mode))
                output = io.BytesIO()
                clean.save(output, format=image_format)
                encoded = output.getvalue()
        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
            SyntaxError,
            Image.DecompressionBombError,
        ):
            raise ApiError(
                415, "unsupported_image", "Upload a valid JPEG, PNG or WebP image."
            ) from None
        if len(encoded) > MAX_IMAGE_BYTES:
            raise ApiError(413, "image_too_large", "The processed image exceeds 5 MiB.")
        extension = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}[image_format]
        relative = f"businesses/{business_id}/{uuid4().hex}.{extension}"
        target = self.resolve(relative)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            # The URL is returned only after this completes and the DB commit succeeds.
            with target.open("xb") as destination:
                destination.write(encoded)
        except FileExistsError:
            raise ApiError(
                503, "storage_unavailable", "Image storage temporarily unavailable."
            ) from None
        except OSError:
            try:
                target.unlink(missing_ok=True)
            except OSError:
                logger.warning("Deferred partial upload cleanup after storage failure.")
            raise ApiError(
                503, "storage_unavailable", "Image storage temporarily unavailable."
            ) from None
        return relative

    def remove(self, path: str) -> None:
        self.resolve(path).unlink(missing_ok=True)


class CatalogMediaService:
    """Coordinate filesystem writes with DB commit; never delete a referenced file."""

    def __init__(self, db: Session, catalog: CatalogService, storage: ImageStorage) -> None:
        self.db = db
        self.catalog = catalog
        self.storage = storage
        self.images = MediaRepository(db)

    def cleanup(self, business_id: str, path: str | None) -> None:
        if path is None or not path.startswith(f"businesses/{business_id}/"):
            return
        try:
            if not self.images.is_referenced(path):
                self.storage.remove(path)
        except (OSError, ApiError, SQLAlchemyError):
            # Cleanup failure must not turn a committed update into a client-visible failure.
            # Leave the file for later maintenance; never guess when the DB is unavailable.
            logger.warning("Deferred image cleanup after storage or database failure.")

    def change(
        self, owner_id: str, business_id: str, product_id: str | None, data: bytes | None
    ) -> BusinessResponse | ProductResponse:
        new_path = None
        try:
            resource = (
                self.catalog.business(owner_id, business_id, lock=True)
                if product_id is None
                else self.catalog.product(owner_id, business_id, product_id, lock=True)
            )
            field = "logo_path" if product_id is None else "image_path"
            old_path = getattr(resource, field)
            new_path = self.storage.save(business_id, data) if data is not None else None
            setattr(resource, field, new_path)
            self.db.flush()
            self.db.refresh(resource, with_for_update=True)
            result = (
                self.catalog.business_response(resource)
                if product_id is None
                else self.catalog.product_response(resource)
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            self.cleanup(business_id, new_path)
            raise
        self.cleanup(business_id, old_path)
        return result

    def delete_product(self, owner_id: str, business_id: str, product_id: str) -> None:
        try:
            product = self.catalog.product(owner_id, business_id, product_id, lock=True)
            path = product.image_path
            self.catalog.products.remove(product)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.cleanup(business_id, path)
