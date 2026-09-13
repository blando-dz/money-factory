"""FastAPI routes for idea generation and retrieval."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from agents.idea_factory import generate_ideas
from api.models.idea import IdeaResponse
from core.database import get_db
from core.models import IdeaModel

router = APIRouter()


@router.post("/generate", response_model=list[IdeaResponse])
async def generate_ideas_endpoint(db: Session = Depends(get_db)) -> Any:
    """Trigger idea generation cycle from arXiv + RSS signals.

    Returns the top-10 ranked ideas and persists them to the database.
    """
    ideas = generate_ideas(max_results=10)

    saved: list[IdeaModel] = []
    for idea in ideas:
        db_idea = IdeaModel(
            title=idea.title,
            problem=idea.problem,
            solution=idea.solution,
            market_fit=idea.market_fit,
            novelty_score=idea.novelty_score,
            feasibility_score=idea.feasibility_score,
            monetizability_score=idea.monetizability_score,
            overall_score=idea.overall_score,
            citations=[c.model_dump() for c in idea.citations],
            created_at=datetime.utcnow(),
        )
        db.add(db_idea)
        saved.append(db_idea)

    db.commit()
    for s in saved:
        db.refresh(s)

    return saved


@router.get("/", response_model=list[IdeaResponse])
async def list_ideas(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> Any:
    """List all ideas ranked by overall score (descending)."""
    ideas = (
        db.query(IdeaModel)
        .order_by(IdeaModel.overall_score.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return ideas


@router.get("/{idea_id}", response_model=IdeaResponse)
async def get_idea(idea_id: int, db: Session = Depends(get_db)) -> Any:
    """Get a single idea by ID."""
    idea = db.query(IdeaModel).filter(IdeaModel.id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    return idea


@router.delete("/{idea_id}")
async def delete_idea(idea_id: int, db: Session = Depends(get_db)) -> Any:
    """Delete an idea by ID."""
    idea = db.query(IdeaModel).filter(IdeaModel.id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    db.delete(idea)
    db.commit()
    return {"status": "deleted", "id": idea_id}
