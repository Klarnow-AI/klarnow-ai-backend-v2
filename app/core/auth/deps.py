from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.auth.jwt import verify_token
from app.core.db.session import get_db
from app.core.errors import UnauthorizedError

# Security scheme: makes Swagger show "Authorize" and send Bearer token
_security = HTTPBearer()


class LazyCurrentUser:
    """Resolve the user row only when non-id fields are actually needed."""

    __slots__ = ("_user_id", "_db", "_loaded_user")

    def __init__(self, user_id: UUID, db: Session):
        object.__setattr__(self, "_user_id", user_id)
        object.__setattr__(self, "_db", db)
        object.__setattr__(self, "_loaded_user", None)

    @property
    def id(self) -> UUID:
        return self._user_id

    @property
    def user(self):
        return self._load()

    def _load(self):
        user = self._loaded_user
        if user is not None:
            return user
        from app.modules.packs.models import User

        user = self._db.query(User).filter(User.id == self._user_id).first()
        if not user:
            raise UnauthorizedError("User not found")
        object.__setattr__(self, "_loaded_user", user)
        return user

    def __getattr__(self, name: str):
        return getattr(self._load(), name)

    def __setattr__(self, name: str, value):
        if name in self.__slots__:
            object.__setattr__(self, name, value)
            return
        if name == "id":
            raise AttributeError("id is read-only")
        setattr(self._load(), name, value)


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
    uid = UUID(user_id)
    return LazyCurrentUser(uid, db)


def get_current_user_record(
    current_user: LazyCurrentUser = Depends(get_current_user),
):
    return current_user.user
