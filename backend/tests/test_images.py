import io
from decimal import Decimal
from pathlib import Path

import pytest
from PIL import Image
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError

from app.core.config import Settings
from app.db.models import Product
from app.services.images import MAX_IMAGE_BYTES, ImageStorage


def image_bytes(format="PNG", size=(8, 8)):
    output = io.BytesIO()
    Image.new("RGB", size, "red").save(output, format=format)
    return output.getvalue()


@pytest.fixture
def image_target(catalog_context):
    c = catalog_context
    product = Product(business_id=c.business.id, name="Cake", price=Decimal("2.50"))
    c.db.add(product)
    c.db.commit()
    return c, product, f"{c.base}/products/{product.id}/image"


def upload(c, url, data=None, filename="../../unsafe.svg", mime="text/html"):
    return c.client.put(
        url,
        headers=c.headers,
        files={"file": (filename, image_bytes() if data is None else data, mime)},
    )


@pytest.mark.parametrize("format", ["PNG", "JPEG", "WEBP"])
@pytest.mark.parametrize("kind", ["logo", "product"])
def test_upload_replace_and_remove(image_target, format, kind):
    c, product, product_url = image_target
    url = f"{c.base}/logo" if kind == "logo" else product_url
    key = "logo_url" if kind == "logo" else "image_url"
    response = upload(c, url, image_bytes(format))
    assert response.status_code == 200, response.text
    public_url = response.json()[key]
    assert public_url.startswith(f"/media/businesses/{c.business.id}/")
    assert "unsafe" not in public_url and ".." not in public_url
    assert not any(field in response.json() for field in ["image_path", "logo_path", "owner_id"])
    image_response = c.client.get(public_url)
    assert image_response.status_code == 200
    assert image_response.headers["x-content-type-options"] == "nosniff"
    assert (
        image_response.headers["content-type"]
        == {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}[format]
    )
    with Image.open(io.BytesIO(image_response.content)) as decoded:
        assert decoded.format == format
    replacement = upload(c, url, image_bytes("PNG")).json()[key]
    assert replacement != public_url
    assert c.client.get(public_url).status_code == 404
    assert c.client.get(replacement).status_code == 200
    assert len(list(c.settings.upload_dir.rglob("*.*"))) == 1
    assert c.client.delete(url, headers=c.headers).status_code == 204
    assert c.client.get(replacement).status_code == 404
    assert not list(c.settings.upload_dir.rglob("*.*"))
    assert c.client.delete(url, headers=c.headers).status_code == 204


@pytest.mark.parametrize(
    "data,status",
    [
        (b"<svg onload='alert(1)'></svg>", 415),
        (b"", 415),
        (b"\x89PNG\r\n\x1a\ntruncated", 415),
        (b"x" * (MAX_IMAGE_BYTES + 1), 413),
        (b"x" * (MAX_IMAGE_BYTES + 65537), 413),
    ],
)
def test_invalid_upload_preserves_existing_image(image_target, data, status):
    c, product, url = image_target
    before = upload(c, url).json()["image_url"]
    response = upload(c, url, data, filename="valid.png", mime="image/png")
    assert response.status_code == status
    assert c.client.get(before).status_code == 200
    assert c.client.get(f"{c.base}/products/{product.id}").json()["image_url"] == before
    assert len(list(c.settings.upload_dir.rglob("*.*"))) == 1


def test_decode_rejects_truncated_image(image_target):
    c, _, url = image_target
    data = image_bytes("JPEG", (128, 128))
    assert upload(c, url, data[:-10]).status_code == 415


def test_dimensions_and_animation_are_bounded(image_target):
    c, _, url = image_target
    data = image_bytes("PNG", (5000, 4001))
    assert len(data) < MAX_IMAGE_BYTES and upload(c, url, data).status_code == 422
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(
        buffer, format="WEBP", save_all=True, append_images=[Image.new("RGB", (8, 8), "blue")]
    )
    assert upload(c, url, buffer.getvalue()).status_code == 422


def test_trailing_content_is_discarded_and_image_is_public(image_target):
    c, _, url = image_target
    marker = b"<script>untrusted trailing content</script>"
    result = upload(c, url, image_bytes() + marker)
    assert result.status_code == 200
    public_url = result.json()["image_url"]
    c.client.cookies.clear()
    response = c.client.get(public_url)
    assert response.status_code == 200 and marker not in response.content


@pytest.mark.parametrize("operation", ["replace", "remove", "delete-product"])
def test_failed_commit_preserves_reference_and_file(image_target, monkeypatch, operation):
    c, product, url = image_target
    before = upload(c, url).json()["image_url"]

    def fail():
        raise OperationalError("private SQL", {}, Exception("private credentials"))

    monkeypatch.setattr(c.db, "commit", fail)
    if operation == "replace":
        response = upload(c, url)
    else:
        target = url if operation == "remove" else f"{c.base}/products/{product.id}"
        response = c.client.delete(target, headers=c.headers)
    assert response.status_code == 503 and "private" not in response.text
    assert c.client.get(before).status_code == 200
    assert c.client.get(f"{c.base}/products/{product.id}").json()["image_url"] == before
    assert len(list(c.settings.upload_dir.rglob("*.*"))) == 1


def test_failed_storage_write_preserves_previous_image(image_target, monkeypatch):
    c, _, url = image_target
    before = upload(c, url).json()["image_url"]
    original_open = Path.open

    def fail_write(path, mode="r", *args, **kwargs):
        if mode == "xb":
            raise PermissionError("private path")
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_write)
    response = upload(c, url)
    assert response.status_code == 503 and "private" not in response.text
    assert c.client.get(before).status_code == 200


def test_shared_references_protect_files_until_last_detach(image_target):
    c, product, url = image_target
    public_url = upload(c, url).json()["image_url"]
    path = public_url.removeprefix("/media/")
    c.business.logo_path = path
    c.db.commit()
    assert c.client.delete(url, headers=c.headers).status_code == 204
    assert c.client.get(public_url).status_code == 200
    assert c.client.delete(f"{c.base}/logo", headers=c.headers).status_code == 204
    assert c.client.get(public_url).status_code == 404


def test_cross_business_reference_is_never_deleted(image_target):
    c, product, url = image_target
    public_url = upload(c, url).json()["image_url"]
    c.foreign.logo_path = public_url.removeprefix("/media/")
    c.db.commit()
    assert c.client.delete(f"{c.base}/products/{product.id}", headers=c.headers).status_code == 204
    assert c.client.get(public_url).status_code == 200
    assert c.db.get(type(c.foreign), c.foreign.id).logo_path == public_url.removeprefix("/media/")


def test_delete_product_cleans_its_image(image_target):
    c, product, url = image_target
    public_url = upload(c, url).json()["image_url"]
    assert c.client.delete(f"{c.base}/products/{product.id}", headers=c.headers).status_code == 204
    assert c.client.get(public_url).status_code == 404
    assert not list(c.settings.upload_dir.rglob("*.*"))


def test_cleanup_failure_does_not_fail_committed_update(image_target, monkeypatch):
    c, product, url = image_target
    upload(c, url)

    def fail_remove(self, path):
        raise OSError("private path")

    monkeypatch.setattr(ImageStorage, "remove", fail_remove)
    response = c.client.delete(url, headers=c.headers)
    assert response.status_code == 204
    assert c.client.get(f"{c.base}/products/{product.id}").json()["image_url"] is None
    assert len(list(c.settings.upload_dir.rglob("*.*"))) == 1


@pytest.mark.parametrize("kind", ["foreign-business", "foreign-product", "sibling-product"])
def test_cross_business_upload_and_removal_fail(image_target, kind):
    c, _, _ = image_target
    business = c.foreign if kind != "sibling-product" else c.sibling
    product = Product(business_id=business.id, name="Private", price=Decimal("1.00"))
    c.db.add(product)
    c.db.commit()
    business_id = business.id if kind == "foreign-business" else c.business.id
    url = f"/api/v1/admin/businesses/{business_id}/products/{product.id}/image"
    assert upload(c, url).status_code == 404
    assert c.client.delete(url, headers=c.headers).status_code == 404
    if kind == "foreign-business":
        logo = f"/api/v1/admin/businesses/{c.foreign.id}/logo"
        assert upload(c, logo).status_code == 404
        assert c.client.delete(logo, headers=c.headers).status_code == 404
    assert not c.settings.upload_dir.exists()


@pytest.mark.parametrize("state", ["missing", "csrf", "origin"])
def test_image_routes_require_owner_and_csrf(image_target, state):
    c, _, product_url = image_target
    if state == "missing":
        c.client.cookies.clear()
    elif state == "csrf":
        c.headers.pop("X-CSRF-Token")
    else:
        c.headers["Origin"] = "http://evil.example.com"
    for url in [product_url, f"{c.base}/logo"]:
        assert upload(c, url).status_code == (401 if state == "missing" else 403)
        assert c.client.delete(url, headers=c.headers).status_code == (
            401 if state == "missing" else 403
        )
    assert not c.settings.upload_dir.exists()


def test_media_rejects_traversal_symlinks_and_unreferenced_files(image_target, tmp_path):
    c, _, url = image_target
    public_url = upload(c, url).json()["image_url"]
    target = c.settings.upload_dir / public_url.removeprefix("/media/")
    target.unlink()
    secret = tmp_path / "private.txt"
    secret.write_text("private content")
    target.symlink_to(secret)
    assert c.client.get(public_url).status_code == 404
    assert c.client.get("/media/%2e%2e/private.txt").status_code == 404
    assert c.client.get("/media/businesses/invalid/image.png").status_code == 404
    orphan = ImageStorage(c.settings.upload_dir).save(c.business.id, image_bytes())
    assert c.client.get(f"/media/{orphan}").status_code == 404
    assert secret.read_text() == "private content"


def test_storage_rejects_symlinked_business_directory(image_target, tmp_path):
    c, _, url = image_target
    directory = c.settings.upload_dir / "businesses"
    directory.mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (directory / c.business.id).symlink_to(elsewhere, target_is_directory=True)
    assert upload(c, url).status_code == 404
    assert list(elsewhere.iterdir()) == []


def test_chunked_oversized_body_is_rejected_before_multipart(image_target):
    c, _, url = image_target

    def chunks():
        for _ in range(7):
            yield b"x" * (1024 * 1024)

    response = c.client.put(
        url,
        content=chunks(),
        headers={**c.headers, "Content-Type": "multipart/form-data; boundary=boundary"},
    )
    assert response.status_code == 413 and response.json()["error"]["code"] == "image_too_large"
    assert not c.settings.upload_dir.exists()


def test_missing_file_has_validation_error(image_target):
    c, _, url = image_target
    response = c.client.put(url, headers=c.headers)
    assert response.status_code == 422 and "file" in response.json()["error"]["fields"]


def test_exact_file_size_limit_is_accepted(image_target):
    c, _, url = image_target
    data = image_bytes()
    data += b"x" * (MAX_IMAGE_BYTES - len(data))
    assert upload(c, url, data).status_code == 200


def test_generated_name_collision_never_removes_existing_file(image_target, monkeypatch):
    from types import SimpleNamespace

    import app.services.images as images_module

    c, _, url = image_target
    public_url = upload(c, url).json()["image_url"]
    generated = Path(public_url).stem
    monkeypatch.setattr(images_module, "uuid4", lambda: SimpleNamespace(hex=generated))
    assert upload(c, url).status_code == 503
    assert c.client.get(public_url).status_code == 200


def test_partial_write_failure_removes_only_new_file(image_target, monkeypatch):
    c, _, url = image_target
    before = upload(c, url).json()["image_url"]
    original_open = Path.open

    class FailedWriter:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()

        def write(self, data):
            self.stream.write(data[:10])
            raise OSError("private disk failure")

    def failing_open(path, mode="r", *args, **kwargs):
        stream = original_open(path, mode, *args, **kwargs)
        return FailedWriter(stream) if mode == "xb" else stream

    monkeypatch.setattr(Path, "open", failing_open)
    assert upload(c, url).status_code == 503
    assert c.client.get(before).status_code == 200
    assert len(list(c.settings.upload_dir.rglob("*.*"))) == 1


def test_replacing_palette_image_preserves_transparency(image_target):
    c, _, url = image_target
    buffer = io.BytesIO()
    palette = Image.new("P", (8, 8))
    palette.save(buffer, format="PNG", transparency=0)
    response = upload(c, url, buffer.getvalue())
    assert response.status_code == 200
    with Image.open(io.BytesIO(c.client.get(response.json()["image_url"]).content)) as decoded:
        assert decoded.convert("RGBA").getpixel((0, 0))[3] == 0


def test_phone_orientation_is_applied_before_metadata_is_removed(image_target):
    c, _, url = image_target
    buffer = io.BytesIO()
    image = Image.new("RGB", (12, 8), "red")
    exif = Image.Exif()
    exif[274] = 6
    image.save(buffer, format="JPEG", exif=exif)
    response = upload(c, url, buffer.getvalue())
    assert response.status_code == 200
    with Image.open(io.BytesIO(c.client.get(response.json()["image_url"]).content)) as decoded:
        assert decoded.size == (8, 12) and not decoded.getexif()


def test_uncertain_commit_never_deletes_a_persisted_new_file(image_target, monkeypatch):
    c, _, url = image_target
    original_commit = c.db.commit

    def fail_after_commit():
        original_commit()
        raise OperationalError("private SQL", {}, Exception("lost acknowledgement"))

    monkeypatch.setattr(c.db, "commit", fail_after_commit)
    assert upload(c, url).status_code == 503
    item_url = url.removesuffix("/image")
    public_url = c.client.get(item_url).json()["image_url"]
    assert public_url is not None and c.client.get(public_url).status_code == 200


@pytest.mark.parametrize("upload_dir", [None, "relative/uploads"])
def test_production_requires_upload_storage_outside_deployment(upload_dir):
    options = {"upload_dir": upload_dir} if upload_dir is not None else {}
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url="sqlite://",
            app_env="production",
            auth_allowed_origins=["https://admin.example.com"],
            admin_base_url="https://admin.example.com",
            storefront_base_url="https://example.com",
            **options,
        )
