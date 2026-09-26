# Job Agent

An AI agent that aggregates live job postings from Greenhouse, Lever, and
RemoteOK, scores each one against a candidate's resume, and surfaces a
ranked shortlist with tailored notes via a Streamlit dashboard.

Built with LangChain/LangGraph for orchestration and the OpenAI API for
resume-fit scoring.

**This tool never submits applications or fills out forms.** It only reads,
aggregates, scores, and summarizes postings — applying is a manual, deliberate
step you take yourself.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # then fill in OPENAI_API_KEY
```

## Configure job sources

Edit `config/companies.yaml` to list the Greenhouse board tokens, Lever
client names, and RemoteOK tags you want to pull from. Board tokens/client
names are the slug in a company's public job board URL and can change as
companies switch applicant-tracking systems — see the comments in that file
for a quick way to verify one before adding it.

## Usage

```bash
# Fetch and print postings from every configured source
python -m job_agent.aggregate

# Parse a resume into a structured profile
python -c "
from job_agent.resume import load_resume_text, extract_resume_profile
text = load_resume_text('data/resume.pdf')
print(extract_resume_profile(text).model_dump_json(indent=2))
"
```

Drop your own resume file at `data/resume.pdf` (`.docx`/`.txt` also supported)
before running the parser — it isn't included in this repo.

Resume parsing uses the OpenAI API for real structured extraction when
`OPENAI_API_KEY` is set, and falls back to a keyword-based heuristic
otherwise (used in tests/CI so nothing requires a live key or network call).

## Tests

```bash
pytest
```

## Project layout

```
src/job_agent/
  connectors/     # Greenhouse, Lever, RemoteOK API clients -> normalized Posting
  resume/         # resume file loading + structured profile extraction
  config.py       # loads config/companies.yaml
  aggregate.py    # fetches from all configured sources, merges results
config/companies.yaml   # which boards/clients/tags to pull from
data/resume.pdf         # your resume (not tracked in this repo)
tests/
```

## Design constraints

- No LinkedIn/Indeed scraping — public JSON APIs only.
- No browser automation (Playwright) in v1.
- No auto-apply / auto-form-fill, ever, without a separate explicit conversation.
