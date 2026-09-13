"""RSS feed parser for tech news sources."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import feedparser

from core.config import get_settings

settings = get_settings()


@dataclass
class RssEntry:
    source: str
    title: str
    link: str
    summary: str
    published: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "title": self.title,
            "link": self.link,
            "summary": self.summary,
            "published": self.published,
        }


def parse_rss_feed(url: str) -> list[RssEntry]:
    """Parse a single RSS feed URL into RssEntry objects.

    Args:
        url: The RSS feed URL.

    Returns:
        List of parsed entries (empty list on failure).
    """
    feed = feedparser.parse(url)
    entries: list[RssEntry] = []
    for entry in feed.entries:
        published = ""
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published = datetime(*entry.published_parsed[:6]).isoformat()
            except (TypeError, ValueError):
                published = getattr(entry, "published", "")
        else:
            published = getattr(entry, "published", "")

        entries.append(
            RssEntry(
                source=feed.feed.get("title", url),
                title=getattr(entry, "title", ""),
                link=getattr(entry, "link", ""),
                summary=getattr(entry, "summary", ""),
                published=published,
            )
        )
    return entries


def fetch_all_feeds(feeds: list[str] | None = None) -> list[RssEntry]:
    """Fetch and parse all configured RSS feeds.

    Args:
        feeds: List of feed URLs. Defaults to settings.

    Returns:
        Combined list of entries from all feeds.
    """
    urls = feeds or settings.rss_feeds_list
    all_entries: list[RssEntry] = []
    for url in urls:
        all_entries.extend(parse_rss_feed(url))
    return all_entries
