"""Fetches postings from every configured source and merges them into one list.

Per-board/client failures (a typo'd board token, a transient network error)
are logged and skipped rather than aborting the whole run — one bad company
in config/companies.yaml shouldn't take down the rest of the fetch.
"""

from __future__ import annotations

import logging

from job_agent.config import SourcesConfig, load_sources_config
from job_agent.connectors import Posting, fetch_greenhouse_jobs, fetch_lever_jobs, fetch_remoteok_jobs

logger = logging.getLogger(__name__)


def fetch_all_postings(config: SourcesConfig | None = None) -> list[Posting]:
    config = config or load_sources_config()
    postings: list[Posting] = []

    for board in config.greenhouse_boards:
        try:
            postings.extend(fetch_greenhouse_jobs(board))
        except Exception:
            logger.warning("Greenhouse fetch failed for board %r", board, exc_info=True)

    for client in config.lever_clients:
        try:
            postings.extend(fetch_lever_jobs(client))
        except Exception:
            logger.warning("Lever fetch failed for client %r", client, exc_info=True)

    if config.remoteok_tags:
        try:
            postings.extend(fetch_remoteok_jobs(config.remoteok_tags))
        except Exception:
            logger.warning("RemoteOK fetch failed", exc_info=True)

    return postings


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = fetch_all_postings()
    print(f"Fetched {len(results)} postings total")
    for p in results[:10]:
        print(f"- [{p.source}] {p.company}: {p.title} ({p.location}) -> {p.url}")
