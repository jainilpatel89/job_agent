"""RemoteOK public API connector.

Endpoint: https://remoteok.com/api
No auth required. There's no per-company board here — it's one global feed
of remote postings, so we filter by tag keywords (e.g. "python", "react")
instead of a company/client identifier.

The API's first array element is always a legal/notice object, not a job —
it's skipped.
"""

from __future__ import annotations

from job_agent.connectors.base import Posting, get_json

URL = "https://remoteok.com/api"


def fetch_remoteok_jobs(tags: list[str] | None = None) -> list[Posting]:
    """Fetch RemoteOK postings, optionally filtered to those matching any tag.

    `tags` is matched case-insensitively against each posting's tag list.
    Pass None (default) to return the entire unfiltered feed.
    """
    data = get_json(URL)

    wanted = {t.lower() for t in tags} if tags else None
    postings: list[Posting] = []

    for job in data:
        if "id" not in job or "position" not in job:
            # Skips the leading legal-notice entry and any malformed rows.
            continue

        job_tags = {t.lower() for t in job.get("tags", [])}
        if wanted is not None and wanted.isdisjoint(job_tags):
            continue

        postings.append(
            Posting(
                source="remoteok",
                source_id=str(job["id"]),
                company=job.get("company", ""),
                title=job.get("position", ""),
                location=job.get("location") or "Remote",
                url=job.get("url", ""),
                description_html=job.get("description", ""),
                department=None,
                posted_at=job.get("date"),
                raw=job,
            )
        )
    return postings
