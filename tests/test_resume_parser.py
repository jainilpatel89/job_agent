import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from job_agent.resume.loader import load_resume_text
from job_agent.resume.parser import ResumeProfile, extract_resume_profile

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RESUME_PDF = DATA_DIR / "resume.pdf"


def test_heuristic_extract_finds_known_skills(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    text = "Jainil Patel\nSkills: React, Node.js, Python, Flutter\n"

    profile = extract_resume_profile(text)

    assert profile.name == "Jainil Patel"
    assert "React" in profile.skills
    assert "Python" in profile.skills


def test_heuristic_extract_finds_education_line(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    text = "Jane Doe\nB.S. Computer Science, University of Georgia\n"

    profile = extract_resume_profile(text)

    assert any("University of Georgia" in line for line in profile.education)


def test_heuristic_skill_match_is_word_boundary(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # "PostgreSQL" contains "sql" as a substring but that shouldn't count as
    # the candidate listing "SQL" separately.
    text = "Jane Doe\nSkills: PostgreSQL\n"

    profile = extract_resume_profile(text)

    assert "PostgreSQL" in profile.skills
    assert "SQL" not in profile.skills


def test_heuristic_extract_parses_experience_entries(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    text = (
        "Jane Doe\n\n"
        "Experience:\n\n"
        "Acme Corp — Software Engineer\n"
        "- Did a thing.\n"
        "- Did another thing.\n\n"
        "Widgets Inc — Intern\n"
        "- Built widgets.\n\n"
        "Education:\n"
        "- B.S. Computer Science, State University\n"
    )

    profile = extract_resume_profile(text)

    assert len(profile.experience) == 2
    first, second = profile.experience
    assert first.organization == "Acme Corp"
    assert first.title == "Software Engineer"
    assert first.highlights == ["Did a thing.", "Did another thing."]
    assert second.organization == "Widgets Inc"
    assert second.title == "Intern"
    assert second.highlights == ["Built widgets."]


def test_heuristic_extract_parses_two_line_column_layout_with_wrapped_bullets(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # Mirrors pypdf's layout-mode extraction of a templated PDF resume:
    # "Org<gap>Location" / "Role<gap>Dates" header pairs, ALL-CAPS section
    # boundaries, and bullet text that wraps onto unmarked indented lines.
    text = (
        "Jane Doe\n\n"
        "WORK EXPERIENCE\n\n\n"
        "Acme Corp                                                   Remote\n"
        "Software Engineer                                    Jan 2024 - Present\n"
        "     ●     Did a thing that wrapped across more than one physical\n"
        "           line of output.\n"
        "     ●     Did another thing.\n\n\n"
        "PROJECTS\n\n\n"
        "Some Project                                                Remote\n"
        "Developer                                                   2025\n"
        "     ●     Built stuff.\n"
    )

    profile = extract_resume_profile(text)

    assert len(profile.experience) == 2
    first, second = profile.experience
    assert first.organization == "Acme Corp"
    assert first.title == "Software Engineer"
    assert first.highlights == [
        "Did a thing that wrapped across more than one physical line of output.",
        "Did another thing.",
    ]
    assert second.organization == "Some Project"
    assert second.title == "Developer"
    assert second.highlights == ["Built stuff."]


@pytest.mark.skipif(not RESUME_PDF.exists(), reason="no real resume.pdf on disk")
def test_heuristic_extract_on_real_resume_pdf():
    text = load_resume_text(RESUME_PDF)

    profile = extract_resume_profile(text, use_llm=False)

    assert profile.name == "Jainil Patel"
    assert "React" in profile.skills
    assert "Python" in profile.skills
    assert "Drizzle ORM" in profile.skills  # multi-word skill split across a column gap
    assert any("University of Georgia" in line for line in profile.education)

    orgs = {entry.organization for entry in profile.experience}
    assert "PicklSpot" in orgs
    assert "Classroom Management Application" in orgs
    assert "AI Image Classifier" in orgs
    picklspot = next(e for e in profile.experience if e.organization == "PicklSpot")
    assert picklspot.title == "Software Engineer Intern"
    assert len(picklspot.highlights) == 3


def test_llm_extract_used_when_api_key_present(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    payload = {
        "name": "Jainil Patel",
        "summary": "Software engineer",
        "skills": ["React", "Python"],
        "experience": [
            {"title": "SWE Intern", "organization": "PicklSpot", "highlights": ["Did stuff."]}
        ],
        "education": ["B.S. Computer Science, University of Georgia"],
    }
    fake_response = MagicMock()
    fake_response.choices = [MagicMock(message=MagicMock(content=json.dumps(payload)))]
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = fake_response

    with patch("openai.OpenAI", return_value=fake_client):
        profile = extract_resume_profile("irrelevant raw text")

    assert isinstance(profile, ResumeProfile)
    assert profile.name == "Jainil Patel"
    assert profile.experience[0].organization == "PicklSpot"
    fake_client.chat.completions.create.assert_called_once()


def test_llm_failure_falls_back_to_heuristic_and_logs(monkeypatch, caplog):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    text = "Jainil Patel\nSkills: React, Python\n"

    with patch("openai.OpenAI", side_effect=RuntimeError("network down")):
        with caplog.at_level("WARNING"):
            profile = extract_resume_profile(text)

    assert profile.name == "Jainil Patel"
    assert "React" in profile.skills
    assert any("falling back to heuristic" in record.message for record in caplog.records)
