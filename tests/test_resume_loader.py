from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from job_agent.resume.loader import load_resume_text

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def test_load_txt_resume(tmp_path):
    path = tmp_path / "resume.txt"
    path.write_text("Jane Doe\nSoftware Engineer\n", encoding="utf-8")

    text = load_resume_text(path)

    assert "Jane Doe" in text


def test_load_unsupported_extension_raises(tmp_path):
    path = tmp_path / "resume.rtf"
    path.write_text("hello")

    with pytest.raises(ValueError, match="Unsupported resume file type"):
        load_resume_text(path)


def test_load_pdf_resume_uses_pypdf_reader_in_layout_mode(tmp_path):
    path = tmp_path / "resume.pdf"
    path.write_bytes(b"%PDF-1.4 fake")

    fake_page = MagicMock()
    fake_page.extract_text.return_value = "Jane Doe\nSoftware Engineer"
    fake_reader = MagicMock()
    fake_reader.pages = [fake_page]

    with patch("pypdf.PdfReader", return_value=fake_reader):
        text = load_resume_text(path)

    assert "Jane Doe" in text
    fake_page.extract_text.assert_called_once_with(extraction_mode="layout")


def test_load_pdf_resume_handles_pages_with_no_extractable_text(tmp_path):
    path = tmp_path / "resume.pdf"
    path.write_bytes(b"%PDF-1.4 fake")

    fake_page = MagicMock()
    fake_page.extract_text.return_value = None
    fake_reader = MagicMock()
    fake_reader.pages = [fake_page]

    with patch("pypdf.PdfReader", return_value=fake_reader):
        text = load_resume_text(path)

    assert text == ""


@pytest.mark.skipif(not (DATA_DIR / "resume.pdf").exists(), reason="no real resume.pdf on disk")
def test_load_real_resume_pdf_end_to_end():
    text = load_resume_text(DATA_DIR / "resume.pdf")

    assert text.strip()
    # Layout mode should keep "Jainil Patel" on one line, not split by word.
    assert "Jainil Patel" in text
