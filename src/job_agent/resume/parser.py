"""Extracts a structured profile (skills/experience/education) from resume text.

Uses the OpenAI API for real extraction when OPENAI_API_KEY is set (this is
what later pipeline stages should rely on for quality). Falls back to a
lightweight keyword/heuristic extraction otherwise, so the rest of the app
stays runnable and testable without hitting the network or spending API
credits — e.g. in CI, or before you've added a key.
"""

from __future__ import annotations

import json
import os
import re

from pydantic import BaseModel, Field

# Seed vocabulary for the offline heuristic fallback. This mirrors the stack
# called out in CLAUDE.md; it's intentionally not exhaustive since the LLM
# path is the real extractor.
KNOWN_SKILLS = [
    "React", "Node.js", "Express", "TypeScript", "JavaScript", "PostgreSQL",
    "Drizzle ORM", "Neon", "Python", "Flutter", "Dart", "BeautifulSoup",
    "Pandas", "OpenAI API", "Better Auth", "Arcjet", "Cloudinary", "Vercel",
    "Railway", "Streamlit", "TensorFlow", "Keras", "MobileNetV2", "REST API",
    "SQL", "Git", "Docker", "LangChain", "LangGraph",
]


class ExperienceEntry(BaseModel):
    title: str
    organization: str
    highlights: list[str] = Field(default_factory=list)


class ResumeProfile(BaseModel):
    name: str | None = None
    summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)


def extract_resume_profile(text: str, use_llm: bool = True) -> ResumeProfile:
    """Parse raw resume text into a `ResumeProfile`.

    Tries the OpenAI extractor first when `use_llm` is True and an API key
    is configured; falls back to `_heuristic_extract` on any failure (missing
    key, network error, malformed response) so this never hard-fails.
    """
    if use_llm and os.environ.get("OPENAI_API_KEY"):
        try:
            return _llm_extract(text)
        except Exception:
            pass
    return _heuristic_extract(text)


def _llm_extract(text: str) -> ResumeProfile:
    from openai import OpenAI

    client = OpenAI()
    schema = ResumeProfile.model_json_schema()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Extract a structured profile from the resume text. "
                    "Respond with JSON matching this schema exactly:\n"
                    f"{json.dumps(schema)}"
                ),
            },
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_object"},
    )
    payload = json.loads(response.choices[0].message.content)
    return ResumeProfile.model_validate(payload)


def _heuristic_extract(text: str) -> ResumeProfile:
    """Offline fallback: keyword-match known skills, split lines for the rest."""
    lower = text.lower()
    skills = [s for s in KNOWN_SKILLS if s.lower() in lower]

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    name = lines[0] if lines else None

    education = [
        line for line in lines
        if re.search(r"\b(university|college|b\.?s\.?|m\.?s\.?|bachelor|master)\b", line, re.I)
    ]

    return ResumeProfile(
        name=name,
        summary=None,
        skills=skills,
        experience=[],
        education=education,
    )
