"""Auth routes: login, register, email sign-in code, and account deletion."""

import secrets
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.auth.deps import get_current_user
from app.core.auth.jwt import create_access_token
from app.core.auth.password import hash_password, verify_password
from app.core.config import get_settings
from app.core.db.session import get_db
from app.core.errors import AppError, UnauthorizedError
from app.modules.packs.models import User, EmailLoginCode, PasswordResetToken

router = APIRouter()

CODE_EXPIRY_MINUTES = 15
RESET_TOKEN_EXPIRY_MINUTES = 60


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class RegisterBody(BaseModel):
    email: EmailStr
    password: str


class SendLoginCodeBody(BaseModel):
    email: EmailStr


class VerifyLoginCodeBody(BaseModel):
    email: EmailStr
    code: str


class CheckEmailBody(BaseModel):
    email: EmailStr


class ForgotPasswordBody(BaseModel):
    email: EmailStr


class ResetPasswordBody(BaseModel):
    token: str
    new_password: str


class ChangePasswordBody(BaseModel):
    current_password: str
    new_password: str


class CheckEmailResponse(BaseModel):
    registered: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _send_login_code_email(to_email: str, code: str) -> bool:
    settings = get_settings()
    if not settings.resend_api_key:
        return False
    try:
        import resend
        resend.api_key = settings.resend_api_key
        resend.Emails.send({
            "from": settings.resend_from_email or "onboarding@resend.dev",
            "to": to_email,
            "subject": "Your Klarnow AI sign-in code",
            "html": f"<p>Your sign-in code is: <strong>{code}</strong></p><p>It expires in {CODE_EXPIRY_MINUTES} minutes. If you didn't request this, you can ignore this email.</p>",
        })
        return True
    except Exception:
        return False


def _send_password_reset_email(to_email: str, token: str) -> bool:
    settings = get_settings()
    if not settings.resend_api_key:
        return False
    base_url = (settings.frontend_url or "http://localhost:3000").rstrip("/")
    reset_url = f"{base_url}/reset-password?token={token}"
    try:
        import resend
        resend.api_key = settings.resend_api_key
        resend.Emails.send({
            "from": settings.resend_from_email or "onboarding@resend.dev",
            "to": to_email,
            "subject": "Reset your Klarnow AI password",
            "html": f"<p>Click the link below to reset your password. It expires in {RESET_TOKEN_EXPIRY_MINUTES} minutes.</p><p><a href=\"{reset_url}\">Reset password</a></p><p>If you didn't request this, you can ignore this email.</p>",
        })
        return True
    except Exception:
        return False


@router.post("/check-email", response_model=CheckEmailResponse)
def check_email(
    body: CheckEmailBody,
    db: Session = Depends(get_db),
):
    """Return whether the email is already registered. No auth required."""
    user = db.query(User).filter(User.email == body.email).first()
    return CheckEmailResponse(registered=user is not None)


@router.post("/send-login-code", status_code=status.HTTP_204_NO_CONTENT)
def send_login_code(
    body: SendLoginCodeBody,
    db: Session = Depends(get_db),
):
    """Generate a 6-digit code, store it, and send it to the email (email sign-in code)."""
    code = "".join(secrets.choice("0123456789") for _ in range(6))
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=CODE_EXPIRY_MINUTES)
    # Remove any existing code for this email
    db.query(EmailLoginCode).filter(EmailLoginCode.email == body.email).delete()
    row = EmailLoginCode(
        email=body.email,
        code=code,
        expires_at=expires_at,
    )
    db.add(row)
    db.commit()
    _send_login_code_email(body.email, code)
    return None


@router.post("/verify-login-code", response_model=TokenResponse)
def verify_login_code(
    body: VerifyLoginCodeBody,
    db: Session = Depends(get_db),
):
    """Verify the code sent to email; create user if new, return JWT."""
    now = datetime.now(timezone.utc)
    row = (
        db.query(EmailLoginCode)
        .filter(
            EmailLoginCode.email == body.email,
            EmailLoginCode.code == body.code.strip(),
            EmailLoginCode.expires_at > now,
        )
        .first()
    )
    if not row:
        raise UnauthorizedError("Invalid or expired code")
    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        user = User(
            email=body.email,
            hashed_password=hash_password(secrets.token_urlsafe(32)),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    db.delete(row)
    db.commit()
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterBody,
    db: Session = Depends(get_db),
):
    """Create a user and return a JWT (for local/dev; tighten in production)."""
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise AppError("Email already registered", status_code=status.HTTP_409_CONFLICT)
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginBody,
    db: Session = Depends(get_db),
):
    """Authenticate with email and password; return JWT."""
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password")
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
def forgot_password(
    body: ForgotPasswordBody,
    db: Session = Depends(get_db),
):
    """If user exists, create a reset token and send email. Always return 204 to avoid email enumeration."""
    user = db.query(User).filter(User.email == body.email).first()
    if user:
        db.query(PasswordResetToken).filter(PasswordResetToken.email == body.email).delete()
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES)
        row = PasswordResetToken(
            email=body.email,
            token=token,
            expires_at=expires_at,
        )
        db.add(row)
        db.commit()
        _send_password_reset_email(body.email, token)
    return None


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    body: ResetPasswordBody,
    db: Session = Depends(get_db),
):
    """Validate token and set new password; token is single-use."""
    now = datetime.now(timezone.utc)
    row = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token == body.token.strip(),
            PasswordResetToken.expires_at > now,
        )
        .first()
    )
    if not row:
        raise AppError("Invalid or expired reset link", status_code=status.HTTP_400_BAD_REQUEST)
    user = db.query(User).filter(User.email == row.email).first()
    if not user:
        raise AppError("Invalid or expired reset link", status_code=status.HTTP_400_BAD_REQUEST)
    user.hashed_password = hash_password(body.new_password)
    db.delete(row)
    db.commit()
    return None


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: ChangePasswordBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change password for the authenticated user."""
    if not verify_password(body.current_password, current_user.hashed_password):
        raise UnauthorizedError("Current password is incorrect")
    current_user.hashed_password = hash_password(body.new_password)
    db.add(current_user)
    db.commit()
    return None


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Permanently delete the authenticated user's account and all related data.
    This removes: login codes, packs (and their brand_os, campaigns,
    proposals, invoices, proofs, websites, plan trackers, etc.), clients,
    chat conversations and messages. The operation cannot be undone.
    """
    # Remove any email login codes and password reset tokens for this user (tables are keyed by email)
    db.query(EmailLoginCode).filter(EmailLoginCode.email == current_user.email).delete()
    db.query(PasswordResetToken).filter(PasswordResetToken.email == current_user.email).delete()
    # Deleting the user cascades to: Pack, Client, Conversation (and Message via Conversation).
    # Pack deletion cascades to all pack-scoped tables (brand_os, campaign, etc.)
    db.delete(current_user)
    db.commit()
    return None
