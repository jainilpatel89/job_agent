"""Extracts a structured profile (skills/experience/education) from resume text.

Uses the OpenAI API for real extraction when OPENAI_API_KEY is set (this is
what later pipeline stages should rely on for quality). Falls back to a
lightweight keyword/heuristic extraction otherwise, so the rest of the app
stays runnable and testable without hitting the network or spending API
credits — e.g. in CI, or before you've added a key.
"""

from __future__ import annotations

import json
import logging
import os
import re

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

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
            logger.warning(
                "LLM resume extraction failed; falling back to heuristic extractor "
                "(lower quality — no experience parsing, keyword-only skills).",
                exc_info=True,
            )
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
    skills = [s for s in KNOWN_SKILLS if _skill_pattern(s).search(lower)]

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    name = lines[0] if lines else None

    education = [
        re.sub(r"\s{2,}", " ", line)  # collapse column-gap whitespace from PDF layout extraction
        for line in lines
        if re.search(r"\b(university|college|b\.?s\.?|m\.?s\.?|bachelor|master)\b", line, re.I)
    ]

    return ResumeProfile(
        name=name,
        summary=None,
        skills=skills,
        experience=_extract_experience_heuristic(text),
        education=education,
    )


def _skill_pattern(skill: str) -> re.Pattern[str]:
    # Word-boundary match so e.g. "SQL" doesn't match inside "PostgreSQL".
    return re.compile(r"\b" + re.escape(skill.lower()) + r"\b")


_EXPERIENCE_HEADER_RE = re.compile(r"^(work\s+)?experience\s*:?\s*$", re.I)
_PROJECTS_HEADER_RE = re.compile(r"^(personal\s+)?projects\s*:?\s*$", re.I)


def _is_other_section_header(stripped: str) -> bool:
    # ALL-CAPS standalone lines ("EDUCATION", "SKILLS") and short "Label:"
    # lines are how resume templates mark section boundaries.
    return stripped.isupper() or (stripped.endswith(":") and len(stripped.split()) <= 4)


def _extract_experience_heuristic(text: str) -> list[ExperienceEntry]:
    """Best-effort extraction of work-experience/project entries + bullet highlights.

    Handles two layouts:
    - a single header line per entry, "Org — Role" (as in a plain-text resume)
    - two header lines per entry, "Org<gap>Location" then "Role<gap>Dates"
      (the column layout `pypdf`'s layout-mode extraction produces from
      templated PDF resumes), with bullets that wrap onto indented
      continuation lines with no marker of their own.

    Both an "Experience"/"Work Experience" section and a following "Projects"
    section are collected into one flat list — project bullets are just as
    relevant to fit-scoring as job history. Any other ALL-CAPS/"Label:"
    section header ends collection until the next relevant section starts.
    """
    entries: list[ExperienceEntry] = []
    current: ExperienceEntry | None = None
    header_complete = True  # True => the next header-ish line starts a new entry
    in_section = False

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue

        if stripped[0] in "-•*●":
            if in_section and current is not None:
                current.highlights.append(re.sub(r"^[-•*●]\s*", "", stripped).strip())
            header_complete = True
            continue

        if _EXPERIENCE_HEADER_RE.match(stripped) or _PROJECTS_HEADER_RE.match(stripped):
            in_section = True
            header_complete = True
            current = None
            continue
        if _is_other_section_header(stripped):
            in_section = False
            continue
        if not in_section:
            continue

        if raw_line[:1].isspace() and current is not None and current.highlights:
            # Wrapped continuation of the previous bullet (no marker of its own).
            current.highlights[-1] = f"{current.highlights[-1]} {stripped}".strip()
            continue

        # Header-ish line: drop a right-hand column (location/dates) separated
        # by a run of 2+ spaces, since only the left column is title/org text.
        left = re.split(r"\s{2,}", stripped, maxsplit=1)[0].strip()

        if header_complete:
            parts = re.split(r"\s+[—–-]\s+", left, maxsplit=1)
            if len(parts) == 2:
                current = ExperienceEntry(organization=parts[0].strip(), title=parts[1].strip(), highlights=[])
                header_complete = True
            else:
                current = ExperienceEntry(organization=left, title="", highlights=[])
                header_complete = False
            entries.append(current)
        else:
            current.title = left
            header_complete = True

    return entries
