"""SQLAlchemy ORM model for Idea table."""
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, JSON

from core.database import Base


class IdeaModel(Base):
    __tablename__ = "ideas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    problem = Column(Text, nullable=False)
    solution = Column(Text, nullable=False)
    market_fit = Column(Text, nullable=False)
    novelty_score = Column(Float, nullable=False)
    feasibility_score = Column(Float, nullable=False)
    monetizability_score = Column(Float, nullable=False)
    overall_score = Column(Float, nullable=False)
    citations = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
