"""API routes module — re-exported from main for test mocking."""
from api.main import (
    analyze_idea,
    get_analysis,
    get_resources,
    scout_resources,
)

__all__ = ["analyze_idea", "get_analysis", "get_resources", "scout_resources"]
