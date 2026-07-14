from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ProfileResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    target_school: str | None
    target_major: str | None
    exam_date: date | None
    current_phase: str | None
    coach_style: str
    timezone: str
    updated_at: datetime


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    target_school: str | None = Field(default=None, max_length=160)
    target_major: str | None = Field(default=None, max_length=160)
    exam_date: date | None = None
    current_phase: str | None = Field(default=None, max_length=80)
    coach_style: str | None = Field(default=None, min_length=1, max_length=80)
    timezone: str | None = Field(default=None, min_length=1, max_length=80)


class RuleFileResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    version: str | None
    path: str
    sha256: str
    content: str


class RulesResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[RuleFileResponse]
    total: int
