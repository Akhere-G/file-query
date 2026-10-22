"""Delete the demo account's projects, files and chats, then rebuild them from example-docs.

Usage (from backend/):
    python -m src.scripts.seed_demo           # prints the target, changes nothing
    python -m src.scripts.seed_demo --apply
"""

import argparse
import logging
import sys

from src.features.demo.demo_seed_service import run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="make changes (without it, only the target DB and bucket are printed)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    return run(args.apply)


if __name__ == "__main__":
    sys.exit(main())
