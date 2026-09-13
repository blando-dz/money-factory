"""API routes module — re-exported from main for test mocking."""
from api.main import (
    analyze_idea,
    get_analysis,
    scout_resources,
    get_resources,
)

__all__ = ["analyze_idea", "get_analysis", "scout_resources", "get_resources"]
