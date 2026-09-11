"""Shared types and HTTP helpers for job source connectors.

Every connector (Greenhouse, Lever, RemoteOK, ...) normalizes its
source-specific JSON into a list of `Posting` objects so the rest of the
pipeline (scoring, dashboard) never needs to know which API a job came from.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import requests

# Identify ourselves honestly; these are public, unauthenticated read-only
# APIs and we're a low-volume personal tool, not a scraper working around
# ToS restrictions (see CLAUDE.md: LinkedIn/Indeed scraping is explicitly
# out of scope for that reason).
USER_AGENT = "job-agent/0.1 (personal job-search tool; contact via GitHub)"

DEFAULT_TIMEOUT = 15


@dataclass
class Posting:
    """A single normalized job posting from any source."""

    source: str  # "greenhouse" | "lever" | "remoteok"
    source_id: str  # id/slug from the origin API, unique within that source
    company: str
    title: str
    location: str | None
    url: str
    description_html: str
    department: str | None = None
    posted_at: str | None = None  # ISO 8601 string if the source provides one
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def uid(self) -> str:
        """Globally unique id across sources, for dedup/caching."""
        return f"{self.source}:{self.source_id}"


def get_json(url: str, params: dict[str, Any] | None = None) -> Any:
    """GET a URL and return parsed JSON, raising on HTTP/network errors."""
    resp = requests.get(
        url,
        params=params,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=DEFAULT_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()
