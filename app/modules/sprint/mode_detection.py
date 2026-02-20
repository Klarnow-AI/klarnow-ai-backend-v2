"""Mode detection for Build vs Improve."""

from sqlalchemy.orm import Session

from app.modules.packs.models import Pack
from app.modules.proof_vault.models import Proof


def detect_sprint_mode(pack: Pack, db: Session) -> str:
    """
    Returns 'improve' if at least 2 of these are true:
    - pack.website_url is not None
    - pack has proof assets (Proof table count > 0)
    - pack.has_existing_customers == True
    
    Otherwise returns 'build'
    """
    criteria_met = 0
    
    if pack.website_url:
        criteria_met += 1
    
    proof_count = db.query(Proof).filter(Proof.pack_id == pack.id).count()
    if proof_count > 0:
        criteria_met += 1
    
    if pack.has_existing_customers:
        criteria_met += 1
    
    return "improve" if criteria_met >= 2 else "build"
