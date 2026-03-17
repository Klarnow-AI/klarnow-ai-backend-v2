"""Waitlist API schemas."""

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field


class WaitlistSubscribeBody(BaseModel):
    email: EmailStr
    first_name: str | None = Field(
        default=None,
        max_length=255,
        alias="firstName",
        validation_alias=AliasChoices("firstName", "first_name", "name"),
    )
    role: str | None = Field(default=None, max_length=255)
    goal: str | None = Field(default=None, max_length=4000)
    source: str | None = Field(default=None, max_length=512)
    website: str | None = Field(default=None, max_length=255)

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )


class WaitlistSubscribeResponse(BaseModel):
    status: str = "subscribed"
    already_subscribed: bool = False
