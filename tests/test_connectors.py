from unittest.mock import patch

from job_agent.connectors.greenhouse import fetch_greenhouse_jobs
from job_agent.connectors.lever import fetch_lever_jobs
from job_agent.connectors.remoteok import fetch_remoteok_jobs

GREENHOUSE_SAMPLE = {
    "jobs": [
        {
            "id": 123,
            "title": "Software Engineer",
            "updated_at": "2026-01-01T00:00:00Z",
            "location": {"name": "Remote"},
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/123",
            "content": "<p>Do software things.</p>",
            "departments": [{"id": 1, "name": "Engineering"}],
        }
    ]
}

LEVER_SAMPLE = [
    {
        "id": "abc-123",
        "text": "Backend Engineer",
        "categories": {"team": "Engineering", "location": "New York"},
        "hostedUrl": "https://jobs.lever.co/acme/abc-123",
        "description": "<p>Build backend things.</p>",
        "createdAt": 1735689600000,
    }
]

REMOTEOK_SAMPLE = [
    {"legal": "this is a legal notice, not a job"},
    {
        "id": "999",
        "position": "Python Developer",
        "company": "RemoteCo",
        "tags": ["python", "backend"],
        "location": "Worldwide",
        "url": "https://remoteok.com/remote-jobs/999",
        "description": "<p>Write Python.</p>",
        "date": "2026-01-01T00:00:00+00:00",
    },
    {
        "id": "1000",
        "position": "Designer",
        "company": "DesignCo",
        "tags": ["design"],
        "location": "Worldwide",
        "url": "https://remoteok.com/remote-jobs/1000",
        "description": "<p>Design things.</p>",
        "date": "2026-01-01T00:00:00+00:00",
    },
]


def test_fetch_greenhouse_jobs():
    with patch("job_agent.connectors.greenhouse.get_json", return_value=GREENHOUSE_SAMPLE):
        postings = fetch_greenhouse_jobs("acme")

    assert len(postings) == 1
    p = postings[0]
    assert p.source == "greenhouse"
    assert p.source_id == "123"
    assert p.title == "Software Engineer"
    assert p.location == "Remote"
    assert p.department == "Engineering"
    assert p.uid == "greenhouse:123"


def test_fetch_lever_jobs():
    with patch("job_agent.connectors.lever.get_json", return_value=LEVER_SAMPLE):
        postings = fetch_lever_jobs("acme")

    assert len(postings) == 1
    p = postings[0]
    assert p.source == "lever"
    assert p.title == "Backend Engineer"
    assert p.location == "New York"
    assert p.department == "Engineering"
    assert p.posted_at is not None


def test_fetch_remoteok_jobs_filters_by_tag():
    with patch("job_agent.connectors.remoteok.get_json", return_value=REMOTEOK_SAMPLE):
        postings = fetch_remoteok_jobs(tags=["python"])

    assert len(postings) == 1
    assert postings[0].title == "Python Developer"
    assert postings[0].company == "RemoteCo"


def test_fetch_remoteok_jobs_no_filter_skips_legal_notice():
    with patch("job_agent.connectors.remoteok.get_json", return_value=REMOTEOK_SAMPLE):
        postings = fetch_remoteok_jobs()

    assert len(postings) == 2
