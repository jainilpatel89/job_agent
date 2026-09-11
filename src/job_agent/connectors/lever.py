"""Lever Postings API connector.

Docs: https://github.com/lever/postings-api
Endpoint: https://api.lever.co/v0/postings/{clientname}?mode=json
No auth required. `client_name` is the slug in a company's public board URL,
e.g. https://jobs.lever.co/netflix -> client_name = "netflix".
"""

from __future__ import annotations

from job_agent.connectors.base import Posting, get_json

BASE_URL = "https://api.lever.co/v0/postings/{client_name}"


def fetch_lever_jobs(client_name: str) -> list[Posting]:
    """Fetch all open postings for one company's Lever board."""
    url = BASE_URL.format(client_name=client_name)
    data = get_json(url, params={"mode": "json"})

    postings: list[Posting] = []
    for job in data:
        categories = job.get("categories", {}) or {}
        postings.append(
            Posting(
                source="lever",
                source_id=str(job["id"]),
                company=client_name,
                title=job.get("text", ""),
                location=categories.get("location"),
                url=job.get("hostedUrl", ""),
                description_html=job.get("description", ""),
                department=categories.get("team"),
                posted_at=_epoch_ms_to_iso(job.get("createdAt")),
                raw=job,
            )
        )
    return postings


def _epoch_ms_to_iso(epoch_ms: int | None) -> str | None:
    if epoch_ms is None:
        return None
    from datetime import datetime, timezone

    return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).isoformat()
