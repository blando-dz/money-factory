"""Tests for Idea Factory Core — TDD approach."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from agents.idea_factory import (
    RawSignal,
    _compute_overall,
    _extract_problem_solution,
    _score_feasibility,
    _score_monetizability,
    _score_novelty,
    _signals_to_idea,
    generate_ideas,
)
from api.models.idea import Citation, IdeaCreate
from integrations.arxiv_client import ArxivPaper, fetch_arxiv_papers
from integrations.rss_parser import RssEntry, parse_rss_feed

# ============================================================
# Unit Tests: Scoring Functions
# ============================================================


class TestScoreNovelty:
    def test_base_score(self):
        score = _score_novelty("Some generic text", set())
        assert 0 <= score <= 100

    def test_tech_terms_boost(self):
        text = "This novel approach achieves state-of-the-art results with breakthrough performance."
        score = _score_novelty(text, set())
        assert score > 50

    def test_duplicate_penalty(self):
        text = "AI-powered workflow automation platform"
        existing = {"ai-powered workflow automation platform"}
        score = _score_novelty(text, existing)
        assert score < 50

    def test_bounds(self):
        assert _score_novelty("", set()) >= 0
        assert _score_novelty("x" * 10000, set()) <= 100


class TestScoreFeasibility:
    def test_base_score(self):
        score = _score_feasibility("A research paper about theory.")
        assert 40 <= score <= 100

    def test_open_source_boost(self):
        score = _score_feasibility("An open source framework with reproducible implementation.")
        assert score > 50

    def test_longer_text_boost(self):
        short = _score_feasibility("Short text.")
        long = _score_feasibility("A" * 300)
        assert long >= short


class TestScoreMonetizability:
    def test_base_score(self):
        score = _score_monetizability("A theoretical analysis.")
        assert 30 <= score <= 100

    def test_saas_boost(self):
        score = _score_monetizability("A SaaS platform for workflow automation and analytics.")
        assert score > 50

    def test_ai_boost(self):
        score = _score_monetizability("AI-powered prediction marketplace.")
        assert score > 50


class TestComputeOverall:
    def test_equal_weights(self):
        # With default weights: 0.35, 0.30, 0.35
        overall = _compute_overall(80, 70, 90)
        expected = 80 * 0.35 + 70 * 0.30 + 90 * 0.35
        assert overall == pytest.approx(expected)

    def test_bounds(self):
        assert _compute_overall(0, 0, 0) == 0
        assert _compute_overall(100, 100, 100) == 100


# ============================================================
# Unit Tests: Signal Processing
# ============================================================


class TestExtractProblemSolution:
    def test_basic_extraction(self):
        text = "Current systems are slow. We propose a new algorithm that is 10x faster."
        problem, solution = _extract_problem_solution(text)
        assert "slow" in problem.lower()
        assert "algorithm" in solution.lower() or "faster" in solution.lower()

    def test_single_sentence(self):
        text = "A novel approach to NLP."
        problem, solution = _extract_problem_solution(text)
        assert "novel approach" in problem.lower()
        assert "automated" in solution.lower()


class TestSignalsToIdea:
    def test_converts_signal(self):
        signals = [
            RawSignal(
                source="arxiv",
                title="Test Paper",
                url="https://arxiv.org/abs/1234",
                text="This paper addresses scalability issues. We present a distributed framework.",
                published="2024-01-01",
            )
        ]
        ideas = _signals_to_idea(signals)
        assert len(ideas) == 1
        assert ideas[0].title == "Test Paper"
        assert len(ideas[0].citations) == 1
        assert ideas[0].citations[0].url == "https://arxiv.org/abs/1234"

    def test_multiple_signals(self):
        signals = [
            RawSignal(source="arxiv", title=f"Paper {i}", url=f"https://arxiv.org/abs/{i}", text=f"Text {i}.")
            for i in range(5)
        ]
        ideas = _signals_to_idea(signals)
        assert len(ideas) == 5


# ============================================================
# Integration Tests: arXiv Client
# ============================================================


class TestArxivClient:
    @patch("integrations.arxiv_client.arxiv.Search")
    def test_fetch_papers(self, mock_search):
        mock_paper = MagicMock()
        mock_paper.entry_id = "https://arxiv.org/abs/2401.00001"
        mock_paper.title = "Test Paper"
        mock_paper.summary = "This is a test summary about AI automation."
        mock_published = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_paper.published = mock_published
        mock_paper.authors = [MagicMock(name="Author One")]
        mock_paper.categories = ["cs.AI"]
        mock_paper.pdf_url = "https://arxiv.org/pdf/2401.00001"

        mock_search.return_value.results.return_value = [mock_paper]

        papers = fetch_arxiv_papers(categories=["cs.AI"], max_results=1)
        assert len(papers) == 1
        assert papers[0].title == "Test Paper"
        assert papers[0].url == "https://arxiv.org/abs/2401.00001"

    @patch("integrations.arxiv_client.arxiv.Search")
    def test_fetch_multiple_categories(self, mock_search):
        mock_search.return_value.results.return_value = []
        papers = fetch_arxiv_papers(categories=["cs.AI", "cs.CE"], max_results=5)
        assert papers == []


# ============================================================
# Integration Tests: RSS Parser
# ============================================================


class TestRssParser:
    @patch("integrations.rss_parser.feedparser.parse")
    def test_parse_feed(self, mock_parse):
        mock_feed = MagicMock()
        mock_feed.feed = {"title": "Hacker News"}
        mock_entry = MagicMock()
        mock_entry.title = "Show HN: My new project"
        mock_entry.link = "https://example.com"
        mock_entry.summary = "A new AI-powered tool."
        mock_entry.published = "Mon, 01 Jan 2024 00:00:00 GMT"
        mock_entry.published_parsed = None
        mock_feed.entries = [mock_entry]
        mock_parse.return_value = mock_feed

        entries = parse_rss_feed("https://hnrss.org/frontpage")
        assert len(entries) == 1
        assert entries[0].title == "Show HN: My new project"
        assert entries[0].source == "Hacker News"

    @patch("integrations.rss_parser.feedparser.parse")
    def test_parse_empty_feed(self, mock_parse):
        mock_feed = MagicMock()
        mock_feed.feed = {"title": "Empty"}
        mock_feed.entries = []
        mock_parse.return_value = mock_feed

        entries = parse_rss_feed("https://example.com/feed")
        assert entries == []


# ============================================================
# Integration Tests: Full Pipeline
# ============================================================


class TestGenerateIdeas:
    @patch("agents.idea_factory.fetch_all_feeds")
    @patch("agents.idea_factory.fetch_arxiv_papers")
    def test_generate_returns_ranked_ideas(self, mock_arxiv, mock_rss):
        mock_arxiv.return_value = [
            ArxivPaper(
                entry_id="https://arxiv.org/abs/2401.001",
                title="AI Automation Framework",
                summary="A novel open source framework for workflow automation using AI.",
                published="2024-01-01T00:00:00",
                authors=["Author"],
                categories=["cs.AI"],
                pdf_url="https://arxiv.org/pdf/2401.001",
            )
        ]
        mock_rss.return_value = [
            RssEntry(
                source="Hacker News",
                title="SaaS Analytics Platform",
                link="https://example.com",
                summary="A new SaaS platform for predictive analytics and optimization.",
                published="2024-01-01",
            )
        ]

        ideas = generate_ideas(max_results=10)
        assert len(ideas) >= 1
        # Verify ranked (descending)
        for i in range(len(ideas) - 1):
            assert ideas[i].overall_score >= ideas[i + 1].overall_score
        # Verify all have citations
        for idea in ideas:
            assert len(idea.citations) >= 1

    @patch("agents.idea_factory.fetch_all_feeds")
    @patch("agents.idea_factory.fetch_arxiv_papers")
    def test_graceful_degradation_arxiv_fails(self, mock_arxiv, mock_rss):
        mock_arxiv.side_effect = Exception("API down")
        mock_rss.return_value = [
            RssEntry(
                source="HN",
                title="Test",
                link="https://example.com",
                summary="AI marketplace platform.",
                published="",
            )
        ]
        ideas = generate_ideas(max_results=5)
        assert len(ideas) >= 1

    @patch("agents.idea_factory.fetch_all_feeds")
    @patch("agents.idea_factory.fetch_arxiv_papers")
    def test_graceful_degradation_rss_fails(self, mock_arxiv, mock_rss):
        mock_arxiv.return_value = [
            ArxivPaper(
                entry_id="https://arxiv.org/abs/2401.001",
                title="Test",
                summary="Novel AI framework.",
                published="",
                authors=[],
                categories=[],
                pdf_url="",
            )
        ]
        mock_rss.side_effect = Exception("Feed down")
        ideas = generate_ideas(max_results=5)
        assert len(ideas) >= 1

    @patch("agents.idea_factory.fetch_all_feeds")
    @patch("agents.idea_factory.fetch_arxiv_papers")
    def test_max_results_limit(self, mock_arxiv, mock_rss):
        mock_arxiv.return_value = [
            ArxivPaper(
                entry_id=f"https://arxiv.org/abs/2401.{i:03d}",
                title=f"Paper {i}",
                summary=f"AI automation framework {i}.",
                published="",
                authors=[],
                categories=[],
                pdf_url="",
            )
            for i in range(20)
        ]
        mock_rss.return_value = []
        ideas = generate_ideas(max_results=5)
        assert len(ideas) <= 5


# ============================================================
# API Tests
# ============================================================


class TestAPI:
    """Test FastAPI endpoints with TestClient."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from fastapi.testclient import TestClient

        from core.database import Base, engine
        from main import create_app

        # Create tables
        Base.metadata.create_all(bind=engine)
        self.app = create_app()
        self.client = TestClient(self.app)

        yield

        # Cleanup
        Base.metadata.drop_all(bind=engine)

    @patch("api.routes.ideas.generate_ideas")
    def test_generate_endpoint(self, mock_generate):
        mock_generate.return_value = [
            IdeaCreate(
                title="Test Idea",
                problem="Problem",
                solution="Solution",
                market_fit="Market",
                novelty_score=80,
                feasibility_score=70,
                monetizability_score=90,
                citations=[Citation(source="arxiv", url="https://arxiv.org/abs/1", title="Test")],
            )
        ]
        # Set overall_score after creation
        mock_generate.return_value[0].overall_score = 80 * 0.35 + 70 * 0.30 + 90 * 0.35

        response = self.client.post("/ideas/generate")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_list_ideas_empty(self):
        response = self.client.get("/ideas/")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_idea_not_found(self):
        response = self.client.get("/ideas/999")
        assert response.status_code == 404

    def test_delete_idea_not_found(self):
        response = self.client.delete("/ideas/999")
        assert response.status_code == 404

    def test_health_endpoint(self):
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
