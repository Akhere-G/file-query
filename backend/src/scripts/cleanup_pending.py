"""Delete uploads that were never confirmed (status 'pending') and their S3 objects.

Usage (from backend/):
    python -m src.scripts.cleanup_pending                  # lists what would be removed
    python -m src.scripts.cleanup_pending --apply
    python -m src.scripts.cleanup_pending --apply --hours 48
"""

import argparse
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from src.database import SessionLocal, engine
from src.features.files import file_service
from src.features.files.file_model import File, FileStatus
from src.settings import settings

logger = logging.getLogger("cleanup_pending")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="delete (default: only count)")
    parser.add_argument("--hours", type=int, default=24, help="minimum age of a pending upload")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info(
        "Target: db=%s bucket=%s",
        engine.url.render_as_string(hide_password=True),
        settings.AWS_BUCKET_NAME,
    )

    with SessionLocal() as db:
        if not args.apply:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=args.hours)
            count = db.scalar(
                select(func.count(File.id)).where(
                    File.status == FileStatus.pending, File.created_at < cutoff
                )
            )
            logger.info("%s pending upload(s) older than %sh. Re-run with --apply.", count, args.hours)
            return 0

        removed = file_service.delete_stale_pending_files(db, args.hours)
        logger.info("Removed %s stale pending upload(s)", removed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
