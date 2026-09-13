"""arXiv API wrapper for fetching research papers."""
from __future__ import annotations

from dataclasses import dataclass

import arxiv

from core.config import get_settings

settings = get_settings()


@dataclass
class ArxivPaper:
    entry_id: str
    title: str
    summary: str
    published: str
    authors: list[str]
    categories: list[str]
    pdf_url: str

    @property
    def url(self) -> str:
        return self.entry_id


def fetch_arxiv_papers(
    categories: list[str] | None = None,
    max_results: int | None = None,
    query: str | None = None,
) -> list[ArxivPaper]:
    """Fetch recent papers from arXiv across specified categories.

    Args:
        categories: arXiv category codes (e.g. cs.AI). Defaults to settings.
        max_results: Max papers to return. Defaults to settings.
        query: Optional search query string.

    Returns:
        List of ArxivPaper objects.
    """
    cats = categories or settings.arxiv_categories_list
    limit = max_results or settings.ARXIV_MAX_RESULTS

    results: list[ArxivPaper] = []
    seen_ids: set[str] = set()

    for category in cats:
        search = arxiv.Search(
            query=f"cat:{category}" + (f" AND {query}" if query else ""),
            max_results=limit,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )
        for paper in search.results():
            if paper.entry_id in seen_ids:
                continue
            seen_ids.add(paper.entry_id)
            results.append(
                ArxivPaper(
                    entry_id=paper.entry_id,
                    title=paper.title,
                    summary=paper.summary,
                    published=paper.published.isoformat() if paper.published else "",
                    authors=[a.name for a in paper.authors],
                    categories=paper.categories,
                    pdf_url=paper.pdf_url,
                )
            )
    return results
