# Welfare Scheme Navigator

**Your Personal Government Scheme Guide**

Welfare Scheme Navigator is an AI-assisted web application that helps Indian citizens explore Central Government and Karnataka State welfare schemes.

It helps users:
- Discover available government welfare schemes.
- Understand scheme details and eligibility conditions.
- Check indicative eligibility using a deterministic rule engine.
- View required document checklists.
- Compare welfare schemes.
- Receive application guidance through an AI assistant.

**Important:** This is an independent prototype, not an official government portal. Eligibility results are indicative only. Final approval is determined by the relevant government authority.

---

## 🏛️ Objectives & Scope

- **Target Communities**: Low-income households, farmers, women, students, gig workers, and senior citizens across Karnataka and India.
- **Key Problem Solved**: Eliminating information asymmetry, complex administrative jargon, and confusion surrounding government welfare eligibility.
- **Strict Anti-Hallucination**:
  - Deterministic Python rule checking separate from Gemini explanations.
  - Zero fabricated eligibility conditions or document lists.
  - Indicative eligibility scoring with clear official disclaimers.
  - Source-grounded RAG retrieval citing official government portals.
- **Privacy First**: Zero collection of sensitive PII (never asks for Aadhaar numbers, PAN, or bank accounts).

---

## 🛠️ Technology Stack

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, Flask |
| Database | SQLite, SQLAlchemy, Flask-SQLAlchemy |
| AI Assistant | Google Gemini API, `google-genai` SDK |
| Scheme Eligibility | Python-based deterministic rule engine |
| Information Retrieval | SQLite FTS5 keyword search |
| Document Processing | PyPDF |
| Frontend | HTML, CSS, JavaScript, Jinja2 |
| Configuration | Python dotenv |
| Testing | Python unittest, pytest |

### Data Management

The prototype uses a locally maintained scheme catalog stored in SQLite. Scheme information is provided through seed data and is not automatically collected from every government website.

---

## 📁 Project Structure
Welfare-Scheme-Navigator/
│
├── agent/
│   ├── __init__.py
│   ├── agent_orchestrator.py
│   ├── conversation_manager.py
│   ├── gemini_client.py
│   ├── prompts.py
│   ├── response_formatter.py
│   └── tools.py
│
├── data/
│   └── schemes_seed.json
│
├── engine/
│   ├── __init__.py
│   ├── document_engine.py
│   ├── eligibility_engine.py
│   └── validator.py
│
├── models/
│   ├── __init__.py
│   ├── citizen.py
│   └── scheme.py
│
├── rag/
│   ├── __init__.py
│   ├── chunker.py
│   ├── citation.py
│   ├── document_loader.py
│   ├── indexer.py
│   ├── retriever.py
│   └── text_extractor.py
│
├── routes/
│   ├── __init__.py
│   ├── api_agent.py
│   ├── api_eligibility.py
│   ├── api_rag.py
│   ├── api_schemes.py
│   └── views.py
│
├── scripts/
│   ├── generate_official_docs.py
│   ├── init_db.py
│   └── seed_schemes.py
│
├── static/
│   ├── css/
│   └── js/
│
├── templates/
│   ├── 404.html
│   ├── 500.html
│   ├── assistant.html
│   ├── base.html
│   ├── compare.html
│   ├── dashboard.html
│   ├── documents.html
│   ├── eligibility.html
│   ├── index.html
│   ├── scheme_detail.html
│   └── schemes.html
│
├── tests/
│   ├── test_assistant_and_compare_fix.py
│   ├── test_phase1.py
│   ├── test_phase2.py
│   ├── test_phase3.py
│   ├── test_phase4.py
│   ├── test_phase5.py
│   ├── test_phase6.py
│   └── test_validation_and_agent_repair.py
│
├── .env.example
├── .gitignore
├── app.py
├── config.py
├── README.md
└── requirements.txt

---

## 🚀 Getting Started

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.11 or later
- Git
- Google Gemini API key (for AI assistant functionality)

### 2. Clone the Repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd YOUR_REPOSITORY_FOLDER
```

Replace the URL and folder name with your actual GitHub repository details.

### 3. Create a Virtual Environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Copy the example configuration:

```powershell
Copy-Item .env.example .env
```

Open `.env` and configure:
- `GEMINI_API_KEY`: Your Gemini API key.
- `SECRET_KEY`: A randomly generated Flask secret key.
- Other settings as required.

Never upload your actual `.env` file to GitHub.

### 6. Initialize and Run

Follow the project's database initialization requirements, then start the application:

```bash
python app.py
```

Open `http://127.0.0.1:8000` in your browser.

### 7. Run Tests

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

### The Six Registered Agent Tools
1. `search_schemes`: Discovery across Karnataka and Central schemes with category/level filters.
2. `retrieve_scheme_information`: SQLite FTS5 BM25 retrieval of official guideline passages with source verification badges (`[VERIFIED OFFICIAL DOCUMENT]`, `[DEMO ONLY - LOCALLY GENERATED MATERIAL]`, `[UNVERIFIED SOURCE]`).
3. `check_eligibility`: Strictly calls deterministic `EligibilityEngine` (4 states: `potentially_eligible`, `not_eligible`, `needs_more_information`, `unable_to_verify`).
4. `get_required_documents`: Generates tailored preparation checklist without requesting file uploads or PII.
5. `compare_schemes`: Compares two or more programs side-by-side with objective difference notes.
6. `get_application_guidance`: Returns ordered step-by-step instructions and official government portal links.

### Conversational REST Endpoints
- `POST /api/agent/chat`: Main multi-turn citizen conversation endpoint with tool calling.
- `GET /api/agent/session/<conversation_id>`: Inspect active session state and profile context.
- `POST /api/agent/reset`: Reset and clear a conversation session.
- `GET /api/agent/status`: Agent readiness and tool registry diagnostics.

---

## ⚖️ Official Disclaimer
*Sahaaya AI provides indicative eligibility assessments only, based on published government guidelines. It does not constitute guaranteed government approval. Final approval is subject to official document verification and processing by competent government departments.*
