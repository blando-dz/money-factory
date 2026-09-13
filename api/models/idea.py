"""Pydantic models for Idea objects."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Citation(BaseModel):
    source: str = Field(..., description="Source type: arxiv, rss, etc.")
    url: str = Field(..., description="Verifiable source URL")
    title: str = Field(default="", description="Title of the source entry")
    published: Optional[str] = None


class Idea(BaseModel):
    id: Optional[int] = None
    title: str
    problem: str
    solution: str
    market_fit: str
    novelty_score: float = Field(ge=0, le=100)
    feasibility_score: float = Field(ge=0, le=100)
    monetizability_score: float = Field(ge=0, le=100)
    overall_score: float = Field(ge=0, le=100)
    citations: list[Citation] = []
    created_at: Optional[datetime] = None


class IdeaCreate(BaseModel):
    title: str
    problem: str
    solution: str
    market_fit: str
    novelty_score: float = Field(ge=0, le=100)
    feasibility_score: float = Field(ge=0, le=100)
    monetizability_score: float = Field(ge=0, le=100)
    overall_score: float = 0
    citations: list[Citation] = []


class IdeaResponse(BaseModel):
    id: int
    title: str
    problem: str
    solution: str
    market_fit: str
    novelty_score: float
    feasibility_score: float
    monetizability_score: float
    overall_score: float
    citations: list[Citation]
    created_at: datetime

    model_config = {"from_attributes": True}
