"""Idea Factory Core — generates ranked project ideas from arXiv + RSS signals."""
from __future__ import annotations

import re
from dataclasses import dataclass

from api.models.idea import Citation, IdeaCreate
from core.config import get_settings
from integrations.arxiv_client import ArxivPaper, fetch_arxiv_papers
from integrations.rss_parser import RssEntry, fetch_all_feeds

settings = get_settings()


# Keywords that signal monetizable problems
MONETIZABLE_SIGNALS = [
    "automation", "marketplace", "saas", "platform", "api",
    "workflow", "analytics", "optimization", "prediction", "ai",
    "machine learning", "nlp", "computer vision", "blockchain",
    "fintech", "healthtech", "edtech", "productivity",
]

FEASIBILITY_SIGNALS = [
    "open source", "framework", "library", "toolkit", "sdk",
    "benchmark", "dataset", "reproducible", "implementation",
]


@dataclass
class RawSignal:
    source: str  # "arxiv" or "rss"
    title: str
    url: str
    text: str
    published: str = ""


def _extract_problem_solution(text: str) -> tuple[str, str]:
    """Heuristically extract problem and solution from text."""
    sentences = re.split(r"[.!?]\s+", text)
    problem = sentences[0] if sentences else text[:200]
    solution = " ".join(sentences[1:3]) if len(sentences) > 1 else "Build an automated solution."
    return problem.strip(), solution.strip()


def _score_novelty(text: str, existing_titles: set[str]) -> float:
    """Score novelty 0-100 based on uniqueness and technical depth."""
    score = 50.0
    tech_terms = ["novel", "new", "first", "unprecedented", "breakthrough", "state-of-the-art"]
    for term in tech_terms:
        if term.lower() in text.lower():
            score += 8
    # Penalize if similar title exists
    for title in existing_titles:
        overlap = set(text.lower().split()) & set(title.lower().split())
        if len(overlap) > 3:
            score -= 15
    return max(0, min(100, score))


def _score_feasibility(text: str) -> float:
    """Score feasibility 0-100 based on implementation signals."""
    score = 40.0
    for signal in FEASIBILITY_SIGNALS:
        if signal.lower() in text.lower():
            score += 10
    if len(text) > 200:
        score += 5
    return max(0, min(100, score))


def _score_monetizability(text: str) -> float:
    """Score monetizability 0-100 based on market signals."""
    score = 30.0
    for signal in MONETIZABLE_SIGNALS:
        if signal.lower() in text.lower():
            score += 12
    return max(0, min(100, score))


def _compute_overall(novelty: float, feasibility: float, monetizability: float) -> float:
    """Weighted overall score."""
    return (
        novelty * settings.WEIGHT_NOVELTY
        + feasibility * settings.WEIGHT_FEASIBILITY
        + monetizability * settings.WEIGHT_MONETIZABILITY
    )


def _signals_to_idea(signals: list[RawSignal]) -> list[IdeaCreate]:
    """Convert raw signals into scored idea candidates."""
    ideas: list[IdeaCreate] = []
    existing_titles: set[str] = set()

    for signal in signals:
        problem, solution = _extract_problem_solution(signal.text)
        citations = [
            Citation(
                source=signal.source,
                url=signal.url,
                title=signal.title,
                published=signal.published,
            )
        ]

        novelty = _score_novelty(signal.text, existing_titles)
        feasibility = _score_feasibility(signal.text)
        monetizability = _score_monetizability(signal.text)

        idea = IdeaCreate(
            title=signal.title[:120],
            problem=problem[:500],
            solution=solution[:500],
            market_fit=f"Market opportunity derived from {signal.source} signal: {signal.title[:80]}",
            novelty_score=novelty,
            feasibility_score=feasibility,
            monetizability_score=monetizability,
            citations=citations,
        )
        existing_titles.add(signal.title.lower())
        ideas.append(idea)

    return ideas


def generate_ideas(
    arxiv_categories: list[str] | None = None,
    rss_feeds: list[str] | None = None,
    max_results: int = 10,
) -> list[IdeaCreate]:
    """Main entry point: fetch signals, score, rank, return top-N ideas.

    Args:
        arxiv_categories: Override arXiv categories.
        rss_feeds: Override RSS feed URLs.
        max_results: Number of top ideas to return.

    Returns:
        Ranked list of IdeaCreate objects.
    """
    signals: list[RawSignal] = []

    # Fetch arXiv papers
    try:
        papers: list[ArxivPaper] = fetch_arxiv_papers(categories=arxiv_categories)
        for p in papers:
            signals.append(
                RawSignal(
                    source="arxiv",
                    title=p.title,
                    url=p.url,
                    text=p.summary,
                    published=p.published,
                )
            )
    except Exception:
        pass  # Graceful degradation

    # Fetch RSS feeds
    try:
        entries: list[RssEntry] = fetch_all_feeds(feeds=rss_feeds)
        for e in entries:
            signals.append(
                RawSignal(
                    source="rss",
                    title=e.title,
                    url=e.link,
                    text=e.summary,
                    published=e.published,
                )
            )
    except Exception:
        pass

    # Convert to ideas
    ideas = _signals_to_idea(signals)

    # Score and rank
    for idea in ideas:
        idea.overall_score = _compute_overall(
            idea.novelty_score, idea.feasibility_score, idea.monetizability_score
        )

    ideas.sort(key=lambda i: i.overall_score, reverse=True)
    return ideas[:max_results]
