"""
Seed proposals and invoices for existing packs.

Run from the repository root:
  uv run python scripts/seed_revenue.py
"""
import sys
from pathlib import Path

# Add the repository root so "app" is importable.
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from datetime import date

from sqlalchemy.orm import Session

from app.core.db.session import SessionLocal
from app.modules.clients.models import Client  # noqa: F401 - register client table for FK
from app.modules.packs.models import Pack
from app.modules.revenue.models import Invoice, Proposal


def seed_revenue(db: Session, max_packs: int = 3) -> tuple[int, int]:
    packs = db.query(Pack).order_by(Pack.created_at.desc()).limit(max_packs).all()
    if not packs:
        print("No packs found. Create packs first.")
        return 0, 0

    proposals_created = 0
    invoices_created = 0

    for pack in packs:
        pack_id = pack.id

        # Proposals: mix of draft, sent, accepted
        existing = db.query(Proposal).filter(Proposal.pack_id == pack_id).count()
        if existing == 0:
            for i, (amount, status) in enumerate(
                [
                    ("2500.00", "draft"),
                    ("1800.00", "sent"),
                    ("3200.00", "accepted"),
                ]
            ):
                p = Proposal(
                    pack_id=pack_id,
                    client_id=None,
                    status=status,
                    amount=amount,
                    currency="USD",
                    due_date=date.today().replace(day=min(28, date.today().day)) if i else None,
                    content={"description": f"Seed proposal {i + 1} for pack"} if i == 0 else None,
                )
                db.add(p)
                proposals_created += 1

        # Invoices: mix of draft, sent, paid
        existing_inv = db.query(Invoice).filter(Invoice.pack_id == pack_id).count()
        if existing_inv == 0:
            for i, (amount, status) in enumerate(
                [
                    ("3200.00", "draft"),
                    ("1500.00", "sent"),
                    ("900.00", "paid"),
                ]
            ):
                inv = Invoice(
                    pack_id=pack_id,
                    client_id=None,
                    status=status,
                    amount=amount,
                    currency="USD",
                    due_date=date.today().replace(day=min(28, date.today().day)) if i else None,
                    content=None,
                )
                db.add(inv)
                invoices_created += 1

    db.commit()
    return proposals_created, invoices_created


def main() -> None:
    db = SessionLocal()
    try:
        p, i = seed_revenue(db, max_packs=5)
        print(f"Created {p} proposals and {i} invoices.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
