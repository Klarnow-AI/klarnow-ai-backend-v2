"""
Clear all data from the database (keeps schema).

Run from project root:
  uv run python scripts/clear_db.py --confirm
"""
import argparse
import os
import sys
from pathlib import Path

# Add project root so "app" is importable
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from sqlalchemy import text

from app.core.config import get_settings
from app.core.db.base import Base
from app.core.db.model_registry import load_model_metadata
from app.core.db.session import engine

load_model_metadata()


def clear_database() -> int:
    """Truncate all tables. Returns number of tables cleared."""
    tables = list(Base.metadata.tables.keys())
    if not tables:
        return 0
    # Quote identifiers so reserved words (e.g. "user") are valid
    quoted = ", ".join(f'"{t}"' for t in tables)
    truncate_sql = text(f"TRUNCATE {quoted} RESTART IDENTITY CASCADE")
    with engine.begin() as conn:
        conn.execute(truncate_sql)
    return len(tables)


def main() -> None:
    parser = argparse.ArgumentParser(description="Clear all data from the database (keeps schema).")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required to run; prevents accidental execution.",
    )
    args = parser.parse_args()

    confirmed = args.confirm or os.environ.get("CONFIRM_CLEAR_DB") == "1"
    if not confirmed:
        print("Run with --confirm or set CONFIRM_CLEAR_DB=1 to clear the database.")
        sys.exit(1)

    settings = get_settings()
    if settings.app_env == "production":
        print("Refusing to clear database when app_env is production.")
        sys.exit(1)

    n = clear_database()
    print(f"Cleared {n} tables.")


if __name__ == "__main__":
    main()
