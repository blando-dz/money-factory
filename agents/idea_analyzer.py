"""
Analyzes ideas for viability using market data, competitor news,
and grounded citations. Scores viability/demand/competition, outputs PASS/REJECT.
"""
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Optional

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    idea_id: str
    idea_title: str
    viability_score: int  # 0-100
    demand_score: int  # 0-100
    competition_score: int  # 0-100
    decision: str  # PASS or REJECT
    confidence: float  # 0.0-1.0
    sources: list[str] = field(default_factory=list)
    reasoning: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def web_search(query: str, limit: int = 5) -> dict[str, Any]:
    """
    Wrapper for web search. In production this calls Hermes web_search;
    here we provide a mockable function for testing.
    """
    try:
        from hermes_tools import web_search as hs_search
        result = hs_search(query=query, limit=limit)
        return result
    except ImportError:
        logger.warning("hermes_tools not available, returning empty search")
        return {"data": {"web": []}}


def polymarket_search(query: str) -> dict[str, Any]:
    """
    Search Polymarket for related markets using the CLOB/Gamma public API.
    No authentication required.
    """
    import urllib.request
    try:
        url = f"https://gamma-api.polymarket.com/markets?search={query}&limit=5&active=true"
        req = urllib.request.Request(url, headers={"User-Agent": "money-factory/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            if isinstance(data, list):
                return {"markets": data}
            return data
    except Exception as e:
        logger.warning(f"Polymarket search failed: {e}")
        return {"markets": []}


class IdeaAnalyzer:
    """
    Analyzes business ideas by:
    1. Searching for existing products/competitors via web search
    2. Checking Polymarket for demand signals
    3. Scoring competition intensity
    4. Computing viability/demand/competition scores
    5. Making PASS/REJECT decision based on thresholds
    """

    # Thresholds
    PASS_VIABILITY = 60
    PASS_CONFIDENCE = 0.5
    MAX_COMPETITION_FOR_PASS = 75

    def analyze(
        self,
        idea_id: str,
        title: str,
        description: str,
        category: str = "general"
    ) -> AnalysisResult:
        """
        Run full analysis pipeline for a single idea.
        """
        # Gather intelligence
        search_results = self.search_competitors(title, category)
        polymarket_data = self.check_polymarket(title, category)

        # Extract sources for grounded citations
        sources = self._extract_sources_from_search(search_results)
        poly_sources = self._extract_sources_from_polymarket(polymarket_data)
        sources.extend(poly_sources)

        # Score dimensions
        demand_score = self._score_demand(polymarket_data.get("markets", []))
        competition_score = self._score_competition(search_results)
        viability_score = self._calculate_viability(demand_score, competition_score, len(sources) > 0)

        # Confidence based on source count and signal quality
        confidence = self._calculate_confidence(sources, polymarket_data.get("markets", []))

        # Decision
        decision = self._make_decision(viability_score, confidence, competition_score)

        # Build reasoning
        reasoning = self._build_reasoning(title, demand_score, competition_score, decision, polymarket_data)

        result = AnalysisResult(
            idea_id=idea_id,
            idea_title=title,
            viability_score=viability_score,
            demand_score=demand_score,
            competition_score=competition_score,
            decision=decision,
            confidence=confidence,
            sources=sources[:10],
            reasoning=reasoning,
            created_at=datetime.utcnow().isoformat()
        )

        # Persist to database if available
        self._save_to_db(result)

        return result

    def search_competitors(self, title: str, category: str) -> dict[str, Any]:
        """Search for existing products and competitors."""
        query = f"{title} {category} competitors products alternatives"
        return web_search(query, limit=8)

    def check_polymarket(self, title: str, category: str) -> dict[str, Any]:
        """Check Polymarket for demand signals."""
        query = f"{title} {category}"
        return polymarket_search(query)

    def _extract_sources_from_search(self, search_results: dict[str, Any]) -> list[str]:
        """Extract URLs from search results for grounded citations."""
        sources = []
        if "data" in search_results and "web" in search_results["data"]:
            for item in search_results["data"]["web"]:
                url = item.get("url", "")
                if url and url.startswith("http"):
                    sources.append(url)
        return sources

    def _extract_sources_from_polymarket(self, poly_data: dict[str, Any]) -> list[str]:
        """Extract Polymarket market URLs as sources."""
        sources = []
        for market in poly_data.get("markets", []):
            slug = market.get("slug", "")
            if slug:
                sources.append(f"https://polymarket.com/event/{slug}")
        return sources

    def _score_demand(self, markets: list[dict]) -> int:
        """
        Score demand (0-100) based on Polymarket market signals.
        High-probability markets with volume indicate real demand.
        """
        if not markets:
            return 30  # Neutral baseline when no market data

        max_demand = 0
        for market in markets:
            try:
                prices = market.get("outcomePrices", "[]")
                if isinstance(prices, str):
                    prices = json.loads(prices)
                volume = float(market.get("volume", 0))

                # Take the highest probability outcome
                high_prob = max(float(p) for p in prices) if prices else 0
                volume_factor = min(volume / 1_000_000, 1.0)  # Cap at $1M volume

                demand = int((high_prob * 70 + volume_factor * 30))
                max_demand = max(max_demand, demand)
            except (ValueError, TypeError):
                continue

        return max(max_demand, 30)

    def _score_competition(self, search_results: dict[str, Any]) -> int:
        """Score competition (0-100, higher = more competitive = worse)."""
        web_results = search_results.get("data", {}).get("web", [])
        n = len(web_results)

        # Check for competitor indicators in results
        competitor_indicators = ["competitor", "alternative", "vs", "comparison", "review"]
        indicator_count = 0
        for item in web_results:
            title = item.get("title", "").lower()
            desc = item.get("description", "").lower()
            for indicator in competitor_indicators:
                if indicator in title or indicator in desc:
                    indicator_count += 1

        # Base score from result count
        if n == 0:
            base = 50
        elif n <= 2:
            base = 25
        elif n <= 5:
            base = 55
        else:
            base = 80

        # Adjust for competitor language
        indicator_bonus = min(indicator_count * 5, 20)
        return min(base + indicator_bonus, 100)

    def _calculate_viability(self, demand_score: int, competition_score: int, has_sources: bool) -> int:
        """
        Calculate overall viability score.
        High demand + low competition = high viability.
        """
        # Invert competition (low competition is good)
        competition_inverted = 100 - competition_score
        viability = int((demand_score * 0.6 + competition_inverted * 0.4))

        # Boost if sources exist (verifiable)
        if has_sources:
            viability = min(viability + 5, 100)

        return max(min(viability, 100), 0)

    def _calculate_confidence(self, sources: list[str], markets: list[dict]) -> float:
        """Calculate confidence score based on data quality."""
        score = 0.3  # Base confidence

        # Sources boost
        source_boost = min(len(sources) * 0.1, 0.4)
        score += source_boost

        # Market data boost
        if markets:
            score += 0.2
            # Volume adds credibility
            for m in markets:
                vol = float(m.get("volume", 0))
                if vol > 100_000:
                    score += 0.1
                    break

        return min(score, 1.0)

    def _make_decision(self, viability: int, confidence: float, competition: int = 50) -> str:
        """
        Make PASS/REJECT decision based on viability and confidence thresholds.
        """
        if viability >= self.PASS_VIABILITY and confidence >= self.PASS_CONFIDENCE:
            if competition <= self.MAX_COMPETITION_FOR_PASS:
                return "PASS"
        return "REJECT"

    def _build_reasoning(
        self,
        title: str,
        demand: int,
        competition: int,
        decision: str,
        poly_data: dict[str, Any]
    ) -> str:
        """Build human-readable reasoning for the decision."""
        parts = [f"Analysis of '{title}':"]

        if demand >= 70:
            parts.append(f"Strong demand signals (score: {demand}/100).")
        elif demand >= 40:
            parts.append(f"Moderate demand (score: {demand}/100).")
        else:
            parts.append(f"Weak demand signals (score: {demand}/100).")

        if competition >= 70:
            parts.append(f"Highly competitive space (score: {competition}/100).")
        elif competition >= 40:
            parts.append(f"Moderate competition (score: {competition}/100).")
        else:
            parts.append(f"Low competition (score: {competition}/100).")

        markets = poly_data.get("markets", [])
        if markets:
            parts.append(f"Found {len(markets)} related prediction market(s).")

        parts.append(f"Decision: {decision}.")
        return " ".join(parts)

    def _save_to_db(self, result: AnalysisResult) -> None:
        """Persist analysis result to database."""
        try:
            from db.storage import save_analysis
            save_analysis(result)
        except ImportError:
            logger.debug("DB storage not available, skipping save")
        except Exception as e:
            logger.warning(f"Failed to save analysis to DB: {e}")

    # Legacy/compat methods for test suite
    def _extract_sources(self, query: str) -> list[str]:
        """Legacy method for extracting sources from a query."""
        results = web_search(query)
        return self._extract_sources_from_search(results)
