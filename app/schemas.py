"""Request and response models for the API."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .prompts import TONES

MAX_TEXT = 5000


class RefineRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TEXT)
    tone: str = "formal"
    context: str | None = Field(default=None, max_length=300)
    save: bool = True

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Please type some text to refine.")
        return v

    @field_validator("tone")
    @classmethod
    def tone_known(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in TONES:
            raise ValueError(f"Tone must be one of: {', '.join(TONES)}")
        return v


class Correction(BaseModel):
    original: str
    corrected: str
    type: str = "other"
    explanation: str = ""


class DiffSegment(BaseModel):
    op: Literal["equal", "insert", "delete"]
    text: str


class RefineResponse(BaseModel):
    id: int | None = None
    created_at: str | None = None
    original: str
    refined: str
    tone: str
    context: str | None = None
    corrections: list[Correction] = []
    tip: str = ""
    diff: list[DiffSegment] = []
    provider: str = ""


class StatsResponse(BaseModel):
    total: int
    by_type: dict[str, int]
