"""Pydantic v2 models for every structured LLM output."""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

Score = Annotated[int, Field(ge=1, le=10)]


class Topic(BaseModel):
    """One interview topic chosen by the planner."""

    name: str = Field(min_length=1)
    why: str = ""
    difficulty: Literal["easy", "medium", "hard"] = "medium"

    @field_validator("difficulty", mode="before")
    @classmethod
    def _norm_difficulty(cls, v: object) -> object:
        return v.strip().lower() if isinstance(v, str) else v


class Plan(BaseModel):
    """Planner output."""

    topics: list[Topic] = Field(min_length=1)
    skill_gaps: list[str] = Field(default_factory=list)
    opening_question: str = Field(min_length=3)


class Evaluation(BaseModel):
    """Evaluator output for a single answer (hidden from the candidate during the interview)."""

    relevance: Score
    depth: Score
    structure: Score
    clarity: Score
    reason: str = ""
    needs_followup: bool = False
    followup_hint: str = ""

    @property
    def average(self) -> float:
        return (self.relevance + self.depth + self.structure + self.clarity) / 4


class Report(BaseModel):
    """Reporter output."""

    overall_score: float = Field(ge=0, le=10)
    per_skill_scores: dict[str, float] = Field(default_factory=dict)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    best_answer: str = ""
    weakest_answer: str = ""
    improved_answer_for_weakest: str = ""
    tips: list[str] = Field(default_factory=list)

    @field_validator("per_skill_scores")
    @classmethod
    def _clamp_skills(cls, v: dict[str, float]) -> dict[str, float]:
        return {k: max(0.0, min(10.0, float(s))) for k, s in v.items()}
