"""Create or repair the demo account's example data.

Usage (from backend/):
    python -m src.scripts.seed_demo                 # dry run
    python -m src.scripts.seed_demo --apply
    python -m src.scripts.seed_demo --apply --delete-messages-after 2026-10-21
"""

import argparse
import logging
import sys
from datetime import datetime, timezone

from src.features.demo.demo_seed_service import run


def parse_cutoff(value: str) -> datetime:
    cutoff = datetime.fromisoformat(value)
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=timezone.utc)
    return cutoff


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="make changes (the default is a dry run)",
    )
    parser.add_argument(
        "--delete-messages-after",
        type=parse_cutoff,
        metavar="DATE",
        help="delete demo messages created after this ISO date/time (UTC if no timezone)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    return run(args.apply, args.delete_messages_after)


if __name__ == "__main__":
    sys.exit(main())
