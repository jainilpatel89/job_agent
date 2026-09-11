from job_agent.resume.parser import extract_resume_profile


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
