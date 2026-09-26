"""Loads raw text out of a resume file, whatever format it's in."""

from __future__ import annotations

from pathlib import Path


def load_resume_text(path: str | Path) -> str:
    """Extract plain text from a .pdf, .docx, or .txt resume file."""
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return _load_pdf(path)
    if suffix == ".docx":
        return _load_docx(path)
    if suffix in (".txt", ".md"):
        return path.read_text(encoding="utf-8")

    raise ValueError(f"Unsupported resume file type: {suffix!r} ({path})")


def _load_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    # Plain extraction mode emits one word per line for some PDF generators
    # (e.g. Canva-style templates), which destroys line/section structure
    # downstream parsing relies on. Layout mode preserves visual line breaks
    # and column spacing instead.
    return "\n".join(
        page.extract_text(extraction_mode="layout") or "" for page in reader.pages
    )


def _load_docx(path: Path) -> str:
    import docx

    doc = docx.Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)
