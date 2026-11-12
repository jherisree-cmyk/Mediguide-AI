"""Request/response models (Pydantic): every input is validated before it reaches the engine."""
from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from api.config import settings

Lang = Literal["en", "te", "hi"]
_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[A-Za-z]{2,24}$")
_CONCEPT = re.compile(r"^[a-z_]{1,40}$")


class RegisterIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=50)
    language: Lang = "en"

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL.match(v):
            raise ValueError("invalid email address")
        return v


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


class ProfileIn(BaseModel):
    display_name: str | None = Field(default=None, max_length=50)
    age_years: float | None = Field(default=None, ge=0, le=120)
    sex: Literal["F", "M"] | None = None
    language: Lang | None = None


class UserOut(BaseModel):
    id: int
    email: str
    display_name: str | None
    age_years: float | None
    sex: str | None
    language: str
    is_admin: bool


class AssessIn(BaseModel):
    text: str = Field(min_length=2, max_length=settings.max_text_chars)
    lang: Lang | None = None              # input language; None = detect automatically
    display_lang: Lang | None = None      # language for the result; None = same as input
    age_years: float | None = Field(default=None, ge=0, le=120)
    save: bool = False                    # keep in history (logged-in users only)


class PreviewIn(BaseModel):
    text: str = Field(min_length=1, max_length=settings.max_text_chars)
    lang: Lang | None = None
    display_lang: Lang | None = None
    age_years: float | None = Field(default=None, ge=0, le=120)


class AnswersIn(BaseModel):
    answers: dict[str, Any]
    followup_token: str | None = Field(default=None, max_length=100)

    @field_validator("answers")
    @classmethod
    def _answers(cls, a: dict[str, Any]) -> dict[str, Any]:
        if len(a) > 30:
            raise ValueError("too many answers")
        clean: dict[str, Any] = {}
        for key, value in a.items():
            if key in ("checklist", "emergency_checklist"):
                if not isinstance(value, list) or len(value) > 25 or not all(
                        isinstance(v, str) and _CONCEPT.match(v) for v in value):
                    raise ValueError(f"{key} must be a list of concept ids")
            elif key == "age":
                if value is not None and (not isinstance(value, (int, float)) or not 0 <= value <= 120):
                    raise ValueError("age must be between 0 and 120")
            elif key == "pain":
                if value is not None and (not isinstance(value, int) or not 0 <= value <= 10):
                    raise ValueError("pain must be an integer 0-10")
            elif key == "pregnant":
                if value not in ("yes", "no"):
                    raise ValueError("pregnant must be 'yes' or 'no'")
            elif key.startswith("onset:") and _CONCEPT.match(key[6:]):
                if value not in ("sudden", "gradual", "unsure"):
                    raise ValueError(f"{key} must be sudden, gradual or unsure")
            elif key.startswith("duration:") and _CONCEPT.match(key[9:]):
                if value not in ("lt1", "d1_4", "d5p"):
                    raise ValueError(f"{key} must be lt1, d1_4 or d5p")
            else:
                raise ValueError(f"unknown answer key {key!r}")
            clean[key] = value
        return clean


class HistoryItem(BaseModel):
    id: str
    created_at: str
    level: str | None
    input_language: str
    text: str | None
    symptoms: list[str]
