"""
FastAPI application for Money Factory Analyzer + Scout agents.
"""
import logging

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

load_dotenv(r"C:\Users\Ghost\.env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Money Factory API",
    description="Multi-Agent Idea → Validate → Plan → Monetize Pipeline",
    version="1.0.0",
)


class IdeaRequest(BaseModel):
    title: str = Field(..., description="Idea title")
    description: str = Field(..., description="Idea description")
    category: str = Field("general", description="Idea category")
    stack_layers: list[str] = Field(
        default_factory=list,
        description="Required stack layers (hosting, database, auth, etc.)"
    )


class AnalysisResponse(BaseModel):
    idea_id: str
    idea_title: str
    viability_score: int
    demand_score: int
    competition_score: int
    decision: str
    confidence: float
    sources: list[str]
    reasoning: str
    created_at: str


class ResourceResponse(BaseModel):
    idea_id: str
    resources: list[dict]
    oss_tools: list[dict]
    total_monthly_cost: float
    cost_breakdown: dict
    feasibility: bool
    created_at: str


@app.get("/")
async def root():
    return {
        "service": "Money Factory API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "money-factory"}


# Analysis endpoints
@app.post("/analysis/{idea_id}", response_model=AnalysisResponse)
async def analyze_idea(idea_id: str, request: IdeaRequest):
    """Analyze an idea for viability, demand, and competition."""
    try:
        from agents.idea_analyzer import IdeaAnalyzer
        analyzer = IdeaAnalyzer()
        result = analyzer.analyze(
            idea_id=idea_id,
            title=request.title,
            description=request.description,
            category=request.category,
        )
        return result.to_dict()
    except Exception as e:
        logger.error(f"Analysis failed for {idea_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analysis/{idea_id}", response_model=AnalysisResponse)
async def get_analysis(idea_id: str):
    """Get the latest analysis for an idea."""
    try:
        from db.storage import get_analysis
        result = get_analysis(idea_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Analysis not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analysis for {idea_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Resource endpoints
@app.post("/resources/{idea_id}", response_model=ResourceResponse)
async def scout_resources(idea_id: str, request: IdeaRequest):
    """Scout free resources and OSS tools for an idea."""
    try:
        from agents.resource_scout import ResourceScout
        scout = ResourceScout()
        layers = request.stack_layers or _infer_layers(request.category)
        manifest = scout.scout(
            idea_id=idea_id,
            title=request.title,
            description=request.description,
            stack_layers=layers,
        )
        return manifest.to_dict()
    except Exception as e:
        logger.error(f"Resource scouting failed for {idea_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/resources/{idea_id}", response_model=ResourceResponse)
async def get_resources(idea_id: str):
    """Get the latest resource manifest for an idea."""
    try:
        from db.storage import get_resources
        result = get_resources(idea_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Resources not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get resources for {idea_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _infer_layers(category: str) -> list[str]:
    """Infer default stack layers from category."""
    base = ["hosting", "database", "auth"]
    if category in ("ai", "ml", "saas"):
        base.append("ai")
    if category in ("web", "saas", "mobile"):
        base.extend(["frontend", "backend"])
    return base
