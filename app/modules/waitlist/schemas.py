"""Waitlist API schemas."""

from pydantic import BaseModel, EmailStr, Field


class WaitlistSubscribeBody(BaseModel):
    email: EmailStr
    name: str | None = Field(default=None, max_length=255)
    source: str | None = Field(default=None, max_length=512)
    website: str | None = Field(default=None, max_length=255)

    model_config = {"extra": "forbid"}


class WaitlistSubscribeResponse(BaseModel):
    status: str = "subscribed"
    already_subscribed: bool = False
