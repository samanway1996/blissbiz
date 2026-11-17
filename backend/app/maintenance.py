"""Run with python3 -m app.maintenance. Dry run unless --apply is supplied."""

import argparse
import json

from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.images import ImageStorage
from app.services.maintenance import MaintenanceService


def main() -> None:
    parser = argparse.ArgumentParser(description="Expired security rows and old orphan images.")
    parser.add_argument("--apply", action="store_true", help="Apply removals; default is dry run.")
    parser.add_argument("--grace-hours", type=int, default=24)
    args = parser.parse_args()
    if not 1 <= args.grace_hours <= 720:
        parser.error("--grace-hours must be between 1 and 720")
    try:
        result = MaintenanceService(SessionLocal, ImageStorage(settings.upload_dir)).run(
            apply=args.apply, grace_hours=args.grace_hours
        )
    except (SQLAlchemyError, OSError):
        raise SystemExit("Maintenance failed: check database/storage availability.") from None
    print(json.dumps(result, sort_keys=True))
    if result["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
