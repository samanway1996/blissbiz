import time
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.db.businesses import BusinessRepository
from app.db.maintenance import MaintenanceRepository
from app.db.media import MediaRepository
from app.db.models import utc_now
from app.services.images import IMAGE_PATH, ImageStorage


class MaintenanceService:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        storage: ImageStorage,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.session_factory = session_factory
        self.storage = storage
        self.clock = clock

    def run(self, *, apply: bool = False, grace_hours: int = 24) -> dict[str, int | bool]:
        if not 1 <= grace_hours <= 720:
            raise ValueError("Use an orphan grace period between 1 and 720 hours.")
        with self.session_factory() as db, db.begin():
            result = {
                **MaintenanceRepository(db).expired(utc_now(), apply=apply),
                "orphan_images": 0,
                "errors": 0,
                "apply": apply,
            }
        cutoff = self.clock() - grace_hours * 3600
        if not self.storage.root.exists():
            return result
        # Do not follow symlinked subdirectories; restrict candidates to generated paths.
        for business_dir in (self.storage.root / "businesses").glob("*"):
            if business_dir.is_symlink() or not business_dir.is_dir():
                continue
            for candidate in business_dir.iterdir():
                relative = candidate.relative_to(self.storage.root).as_posix()
                if IMAGE_PATH.fullmatch(relative) is None:
                    continue
                try:
                    path = self.storage.resolve(relative)
                    if not path.is_file() or path.stat().st_mtime >= cutoff:
                        continue
                    # A fresh transaction per candidate avoids stale repeatable-read snapshots.
                    # Upload/delete operations hold this same business lock until commit.
                    with self.session_factory() as db, db.begin():
                        BusinessRepository(db).lock_id(business_dir.name)
                        if MediaRepository(db).is_referenced(relative):
                            continue
                        path = self.storage.resolve(relative)
                        if path.is_file() and path.stat().st_mtime < cutoff:
                            result["orphan_images"] += 1
                            if apply:
                                self.storage.remove(relative)
                except (OSError, ApiError):
                    result["errors"] += 1
        return result
