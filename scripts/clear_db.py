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
from app.core.db.session import engine

# Import all model modules so Base.metadata is fully populated
from app.modules.agents import models as agents_models  # noqa: F401
from app.modules.brand_os import models as brand_os_models  # noqa: F401
from app.modules.builder import models as builder_models  # noqa: F401
from app.modules.campaign import models as campaign_models  # noqa: F401
from app.modules.chat import models as chat_models  # noqa: F401
from app.modules.clients import models as clients_models  # noqa: F401
from app.modules.conversion_page import models as conversion_page_models  # noqa: F401
from app.modules.creative import models as creative_models  # noqa: F401
from app.modules.packs import models as packs_models  # noqa: F401
from app.modules.proof_vault import models as proof_vault_models  # noqa: F401
from app.modules.revenue import models as revenue_models  # noqa: F401
from app.modules.response_rules import models as response_rules_models  # noqa: F401
from app.modules.sprint import models as sprint_models  # noqa: F401
from app.modules.subscription import models as subscription_models  # noqa: F401
from app.modules.tasks import models as tasks_models  # noqa: F401


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
