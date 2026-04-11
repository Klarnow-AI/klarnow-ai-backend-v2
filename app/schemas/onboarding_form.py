"""Onboarding form submission schema.

The strict 6-question business brief per ONBOARDING_FORM_SPEC.md.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class OnboardingFormSubmission(BaseModel):
    """Exactly 6 required answers from the MVP onboarding form."""

    model_config = ConfigDict(extra="forbid")

    question_1_identity_and_location: str = Field(
        ...,
        min_length=20,
        max_length=300,
        description="What is your business called, what do you do, and where do you operate?",
    )
    question_2_offer: str = Field(
        ...,
        min_length=20,
        max_length=400,
        description="What do you offer, and what does a typical customer buy from you?",
    )
    question_3_customer_and_problem: str = Field(
        ...,
        min_length=20,
        max_length=400,
        description="Who is your ideal customer, and what problem are they trying to solve?",
    )
    question_4_differentiation: str = Field(
        ...,
        min_length=20,
        max_length=400,
        description="Why should someone choose you over other options?",
    )
    question_5_goals: str = Field(
        ...,
        min_length=10,
        max_length=300,
        description="What are your top goals in the next 3 to 6 months?",
    )
    question_6_founder_story_and_brand_feeling: str = Field(
        ...,
        min_length=20,
        max_length=500,
        description="Why did you start this business, and how do you want people to feel when they interact with your brand?",
    )
