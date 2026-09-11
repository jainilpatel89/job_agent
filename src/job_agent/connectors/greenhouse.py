"""Greenhouse Job Board API connector.

Docs: https://support.greenhouse.io/hc/en-us/articles/10568627186203
Endpoint: https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs
No auth required. `board_token` is the slug in a company's public board URL,
e.g. https://boards.greenhouse.io/stripe -> board_token = "stripe".
"""

from __future__ import annotations

from job_agent.connectors.base import Posting, get_json

BASE_URL = "https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"


def fetch_greenhouse_jobs(board_token: str) -> list[Posting]:
    """Fetch all open postings for one company's Greenhouse board."""
    url = BASE_URL.format(board_token=board_token)
    data = get_json(url, params={"content": "true"})

    postings: list[Posting] = []
    for job in data.get("jobs", []):
        location = job.get("location", {}).get("name")
        departments = job.get("departments") or []
        department = departments[0]["name"] if departments else None

        postings.append(
            Posting(
                source="greenhouse",
                source_id=str(job["id"]),
                company=board_token,
                title=job.get("title", ""),
                location=location,
                url=job.get("absolute_url", ""),
                description_html=job.get("content", ""),
                department=department,
                posted_at=job.get("updated_at"),
                raw=job,
            )
        )
    return postings
