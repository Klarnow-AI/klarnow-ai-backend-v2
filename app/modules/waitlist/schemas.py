"""Waitlist API schemas."""

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    model_validator,
)


class WaitlistSubscribeBody(BaseModel):
    email: EmailStr
    first_name: str | None = Field(
        default=None,
        max_length=255,
        alias="firstName",
        validation_alias=AliasChoices("firstName", "first_name", "name"),
    )
    role: str | None = Field(default=None, max_length=255)
    source: str | None = Field(default=None, max_length=512)
    website: str | None = Field(default=None, max_length=255)

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )

    @model_validator(mode="before")
    @classmethod
    def drop_legacy_goal(cls, data):
        if isinstance(data, dict) and "goal" in data:
            cleaned = dict(data)
            cleaned.pop("goal", None)
            return cleaned
        return data


class WaitlistSubscribeResponse(BaseModel):
    status: str = "subscribed"
    already_subscribed: bool = False
