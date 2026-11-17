import io
import os
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from PIL import Image
from sqlalchemy.orm import Session

from app.db.models import BrowserSession, Product, RateLimitBucket, utc_now
from app.services.images import ImageStorage
from app.services.maintenance import MaintenanceService


def test_maintenance_dry_run_apply_grace_and_references(db, existing_business, tmp_path):
    storage = ImageStorage(tmp_path / "uploads")
    data = io.BytesIO()
    Image.new("RGB", (4, 4)).save(data, format="PNG")
    referenced = storage.save(existing_business.id, data.getvalue())
    orphan = storage.save(existing_business.id, data.getvalue())
    recent = storage.save(existing_business.id, data.getvalue())
    for path in (referenced, orphan):
        os.utime(storage.resolve(path), (0, 0))
    db.add(
        Product(
            business_id=existing_business.id,
            name="Draft image",
            price=Decimal("1.00"),
            image_path=referenced,
        )
    )
    expired_hash, active_hash, rate_hash = [uuid4().hex * 2 for _ in range(3)]
    now = utc_now()
    db.add_all(
        [
            BrowserSession(
                token_hash=expired_hash, csrf_token="x" * 43, expires_at=now - timedelta(days=1)
            ),
            BrowserSession(
                token_hash=active_hash, csrf_token="y" * 43, expires_at=now + timedelta(days=1)
            ),
            RateLimitBucket(
                key_hash=rate_hash, attempt_count=1, expires_at=now - timedelta(days=1)
            ),
        ]
    )
    db.commit()

    def factory():
        return Session(bind=db.get_bind(), join_transaction_mode="create_savepoint")

    service = MaintenanceService(factory, storage)
    preview = service.run()
    assert preview["orphan_images"] == 1 and preview["browser_sessions"] >= 1
    assert storage.resolve(orphan).exists() and db.get(BrowserSession, expired_hash) is not None
    result = service.run(apply=True)
    db.expire_all()
    assert result["orphan_images"] == 1 and result["errors"] == 0
    assert not storage.resolve(orphan).exists()
    assert storage.resolve(referenced).exists() and storage.resolve(recent).exists()
    assert (
        db.get(BrowserSession, expired_hash) is None and db.get(RateLimitBucket, rate_hash) is None
    )
    assert db.get(BrowserSession, active_hash) is not None


def test_maintenance_ignores_unknown_paths_and_symlinks(db, existing_business, tmp_path):
    storage = ImageStorage(tmp_path / "uploads")
    root = storage.root / "businesses" / existing_business.id
    root.mkdir(parents=True)
    secret = tmp_path / "keep.txt"
    secret.write_text("keep")
    (root / f"{uuid4().hex}.png").symlink_to(secret)
    (root / "unknown.txt").write_text("keep")
    service = MaintenanceService(
        lambda: Session(bind=db.get_bind(), join_transaction_mode="create_savepoint"), storage
    )
    result = service.run(apply=True)
    assert result["orphan_images"] == 0 and secret.read_text() == "keep"
    assert (root / "unknown.txt").read_text() == "keep"


@pytest.mark.parametrize("hours", [0, -1, 721])
def test_maintenance_rejects_unsafe_grace(db, tmp_path, hours):
    service = MaintenanceService(lambda: db, ImageStorage(tmp_path))
    with pytest.raises(ValueError):
        service.run(grace_hours=hours)
