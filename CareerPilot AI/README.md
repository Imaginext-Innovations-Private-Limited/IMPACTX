# CareerPilot AI

CareerPilot AI is a local-first Skills-to-Jobs Career Agent for students preparing for technology roles. It helps students understand their current skills, identify gaps, plan focused learning, and practise interviews.

**Problem statement:** #13, Skills-to-Jobs Career Agent  
**Track:** D, Education and Future of Work  
**Tagline:** From Skills to Success.

## Features

- Account-based private workspace with overview, resume, GitHub, career match, roadmap, interview, and progress sections.
- PDF resume text extraction with PyMuPDF, configurable skill phrase matching, and best-effort education, experience, and project sections. Resume bytes and full extracted text are not saved.
- Explainable comparison for Python Developer, Data Analyst, Machine Learning Engineer, Frontend Developer, and Full Stack Developer. Required skills contribute 85% of the score and preferred skills contribute 15%; it is not an employment or hiring probability. Perfect Match means all mandatory skills are present, while 100% requires every mandatory and preferred skill.
- Public GitHub profile analysis through the unauthenticated REST API, including repository descriptions, languages, stars, forks, update dates, and role relevance. Only explicit skill mentions in repository descriptions can add match evidence; programming-language metadata alone is not treated as proficiency.
- Minimum mandatory-skill enhancement recommendations, role-ordered priorities, and a personalized roadmap action only when mandatory gaps remain. A perfect mandatory match is clearly identified and does not require a roadmap.
- Four-week learning roadmap generated locally through Ollama when available, with a deterministic fallback and curated free resource names.
- Four-question mock interview with per-answer feedback, strengths, improvement areas, and a final practice summary. Feedback is not an employer assessment.
- SQLite persistence for profiles, analysis history, roadmaps and task completion, GitHub snapshots, and interview sessions and answers. All records are scoped to their owner.
- Chart.js visualizations use the signed-in student's actual saved data.

## Technology

- Python 3.11+
- Django 5.2 and SQLite
- PyMuPDF and Requests
- Ollama with `qwen2.5:3b` for local AI inference
- Bootstrap 5, custom CSS, Bootstrap Icons, and Chart.js

Bootstrap, icons, fonts, and Chart.js are loaded from their public CDNs. Resume parsing and match computation run in the Django process. AI inference runs locally through Ollama at `http://localhost:11434`; no paid AI API is used.

## Architecture

- `career/views.py` handles authentication, ownership-scoped requests, validation, and response flow.
- `career/services/resume.py` extracts PDF text, sections, and configured skill phrases.
- `career/services/matching.py` stores role profiles and computes the explainable score.
- `career/services/github.py` requests public GitHub data and ranks repositories against a role.
- `career/services/ollama.py` validates structured roadmap output and supplies the fallback.
- `career/services/interview.py` generates role-specific questions, evaluates answers, and summarizes practice.
- `career/models.py` stores user-owned career records; `career/migrations/` contains their schema.
- `career/templates/career/` and `career/static/career/` provide the landing, account, and responsive workspace UI.

## Windows Setup

Requirements: Windows 10/11 and Python 3.11, 3.12, 3.13, or 3.14. Ollama is optional; the roadmap and interview flows have built-in Python fallbacks.

### First-time setup

1. Install a supported Python version from [python.org](https://www.python.org/downloads/windows/). Select **Add python.exe to PATH** during installation.
2. Open the project folder in File Explorer.
3. Double-click `setup_project.bat` and wait for the success message. It creates `.venv`, syncs `requirements.txt`, applies pending migrations, and runs Django checks.

Alternatively, double-click `start_project.bat`; it performs the same setup checks before starting the server.

### Everyday startup and stopping

Double-click `start_project.bat`. It activates `.venv`, installs dependencies only when `requirements.txt` changes or a required package is missing, applies any pending migrations, checks Ollama, starts Django, and opens http://127.0.0.1:8000/. Keep the terminal window open to see logs and errors. On the first visit, create an account to use the private workspace.

To stop the server, press **Ctrl+C** in that terminal and wait for it to stop. If Windows asks whether to terminate a batch job, type `Y`. `stop_project.bat` displays these instructions. Do not close the window by deleting/terminating the process or delete `db.sqlite3`.

### Dependencies

Add a runtime package to `requirements.txt` using a version range, for example `package-name>=1.2,<2`. Then run `setup_project.bat` or `start_project.bat`; the setup syncs the changed requirements into `.venv` and records the requirements file hash locally. It skips installation when the manifest is unchanged and all declared packages are already present.

For manual installation, open Command Prompt in the project folder and run:

```bat
.venv\Scripts\activate.bat
python -m pip install package-name
```

Also add the package (and an appropriate version constraint) to `requirements.txt` so another setup can reproduce it. Do not install project packages globally.

### Ollama

Ollama is optional. The launcher checks whether its command is installed, whether the server at http://localhost:11434 responds, and whether `qwen2.5:3b` is available. It never downloads the model automatically. To use local AI, install Ollama, start it, then choose when to download the model:

```bat
ollama pull qwen2.5:3b
ollama list
```

If Ollama or the model is unavailable, the Django app still starts and uses its built-in Python fallback. See [Ollama Setup](#ollama-setup) for model configuration.

### Windows troubleshooting

- **Python not found / incompatible version:** install Python 3.11–3.14, enable **Add python.exe to PATH**, and reopen File Explorer or Command Prompt.
- **Virtual environment creation failed:** confirm the project folder is writable. If `.venv` is incomplete, rename that specific `.venv` folder and rerun setup; the project database is separate and is not removed.
- **Dependency installation failed:** check internet/proxy access and verify the package/version syntax in `requirements.txt`, then rerun the launcher.
- **Migration failed:** read the Django error in the open window and check that the configured database is accessible and writable. The launcher runs only `migrate --noinput`; it never resets or deletes data.
- **Port 8000 is occupied:** stop the other development server, or use `netstat -ano | findstr :8000` to identify the process. Do not terminate an unfamiliar process.
- **Ollama unavailable or model missing:** start the Ollama app/server. Only if you want AI features, run `ollama pull qwen2.5:3b`; the Python fallback remains available.
- **Server exits during startup:** leave the terminal open and use the displayed Django error to troubleshoot. Rerun `setup_project.bat` after correcting the issue.

### GitHub and the shared team folder

For a shared Windows laptop, all four members can use this same project folder and its local SQLite database. Run only one development server at a time. The `.venv`, database, `.env`, media, and local temporary files are ignored by Git and must not be uploaded. Do not put credentials, private resumes, or other user data in commits.

To publish the source to a GitHub repository, create an empty repository on GitHub (do not initialize a second README if this project already has one), then in Command Prompt at the project folder:

```bat
git init
git add .
git status
git commit -m "Initial CareerPilot AI project"
git branch -M main
git remote add origin https://github.com/YOUR-TEAM/YOUR-REPOSITORY.git
git push -u origin main
```

Review `git status` before every commit to confirm `.venv`, `db.sqlite3`, `.env`, media, and local data are not staged. Replace the remote URL with the team's repository URL.

For local development, Django generates an ephemeral secret key if `DJANGO_SECRET_KEY` is not set. Before deployment, set `DJANGO_SECRET_KEY`, set `DJANGO_DEBUG=false`, and configure `DJANGO_ALLOWED_HOSTS` for the deployment host. Do not commit credentials or production secrets.

## Ollama Setup

Install Ollama, then pull the free model and make sure its local service is running:

```powershell
ollama pull qwen2.5:3b
ollama list
```

CareerPilot calls Ollama's local `/api/generate` endpoint. To use another locally installed model, set `CAREER_OLLAMA_MODEL` before starting Django. If Ollama is stopped or returns malformed data, roadmaps and interview feedback fall back to built-in logic.

The role skill vocabulary can be overridden with the comma-separated `CAREER_SKILL_KEYWORDS` environment variable. If it is unset, CareerPilot uses the built-in dictionary.

## Usage

1. Create an account and upload a text-based PDF from **Resume Analyzer**.
2. Select a target role and review the indicative match score, match category, required/preferred skills, resume sections, and explanation. Optional GitHub analysis can add explicit project-description evidence, but missing GitHub data does not lower the score.
3. Optionally enter a public GitHub username in **GitHub Analyzer**. GitHub's unauthenticated API rate limits apply; no token is required or exposed.
4. Generate a four-week plan and mark tasks complete to track progress.
5. Start a mock interview, answer four questions, and review immediate feedback and the final summary.

The account owns its saved career records. Uploaded resume files and full extracted resume text are not stored. Avoid uploading documents you do not have permission to process.

## Testing

```powershell
python manage.py check
python manage.py makemigrations --check
python manage.py test career.tests
```

Service tests mock GitHub and Ollama network calls for repeatability. A live Ollama instance is not required for the test suite.

## Screenshots

The interface includes a public landing page and authenticated overview, analysis, roadmap, interview, and progress screens. Screenshots can be added here after capture from the running local app.

## Team Contribution

- Resume extraction and configurable skill analysis: `career/services/resume.py`
- Role data and explainable scoring: `career/services/matching.py`
- Public portfolio analysis: `career/services/github.py`
- Local AI roadmap and interview support: `career/services/ollama.py`, `career/services/interview.py`
- Authentication, persistence, and user data isolation: `career/views.py`, `career/models.py`
- Product UI and responsive layouts: `career/templates/career/`, `career/static/career/`

Add team member names and individual contributions here before the hackathon submission.

## Limitations

- Scanned/image-only PDFs are not OCR processed and may not yield readable text.
- Skill recognition uses a configurable phrase dictionary; it is transparent but does not infer proficiency or verify claims.
- GitHub analysis covers public repository metadata returned by the public API, not private work or full source-code quality.
- Match scores are heuristic comparisons, not hiring predictions. Interview feedback is practice guidance, not an employer assessment.
