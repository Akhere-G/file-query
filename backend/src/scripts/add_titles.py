"""Give chunks that have no title one, using CHUNK_TITLE_MODE (heuristic or llm).

Usage (from backend/):
    python -m src.scripts.add_titles            # prints how many chunks lack a title
    python -m src.scripts.add_titles --apply
"""

import argparse
import logging

from sqlalchemy import func, select
from src.database import SessionLocal, engine
from src.features.files.file_model import Chunk
from src.features.files.file_processing_service import make_chunk_title
from src.settings import settings

logger = logging.getLogger("add_titles")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="make changes")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info(
        "Target: db=%s mode=%s",
        engine.url.render_as_string(hide_password=True),
        settings.CHUNK_TITLE_MODE,
    )

    with SessionLocal() as db:
        missing = db.scalar(select(func.count(Chunk.id)).where(Chunk.title.is_(None)))
        logger.info("%s chunk(s) have no title", missing)
        if not args.apply:
            logger.info("Nothing was changed. Re-run with --apply.")
            return 0

        for chunk in db.scalars(select(Chunk).where(Chunk.title.is_(None))):
            chunk.title = make_chunk_title(chunk.content)
        db.commit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
