from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.auth.jwt import verify_token
from app.core.db.session import get_db
from app.core.errors import UnauthorizedError

# Security scheme: makes Swagger show "Authorize" and send Bearer token
_security = HTTPBearer()


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
) -> str:
    if credentials is None:
        raise UnauthorizedError("Missing or invalid Authorization header")
    payload = verify_token(credentials.credentials)
    return payload.sub


def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    from app.modules.packs.models import User

    uid = UUID(user_id)
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise UnauthorizedError("User not found")
    return user