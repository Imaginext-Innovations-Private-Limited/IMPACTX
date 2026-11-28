# Requirements to implementation

The uploaded specification is included as Requirements.docx. The browser menu provides 14 citizen destinations. The separately authenticated admin portal has eight destinations. The table gives the normal entry point and the observation to check.

| No. | Section | Check on a fresh laptop |
|---:|---|---|
| 1 | Dashboard | Local scheme count and household progress; find schemes, search or select a category. |
| 2 | AI Navigator | Adaptive typed/voice questions, skip, edit, back, restart, manual results and sourced Q&A. |
| 3 | Eligibility Checker | Check a profile or manual answers. Open pass/fail/unknown inputs and the clause behind each result. |
| 4 | Explore Schemes | Search and filter by central/state, category, age, income. Open details, evidence and current official route. |
| 5 | Family Welfare Navigator | Consent, add/select/edit/remove members, separate saved answers and suggested schemes per member. |
| 6 | Scheme Comparison | Compare two or three distinct schemes with dates, steps and evidence. Unsourced combination rules require official confirmation. |
| 7 | Eligibility Simulator | Run hypothetical values against the same rules and inspect which criteria changed. Saved answers are isolated. |
| 8 | Document Checklist | Required/conditional items, address-dependent evidence, ready count, acquisition guidance and local persistence. |
| 9 | AI Document Scanner | Validated image/PDF, local OCR or PDF text, confidence where available, original next to editable suggestions. Confirm before copying fields. |
| 10 | Application Assistant | Confirmed prefill, required preparation fields, edit, preview, export PDF and official handoff. Uses the recorded form or labelled preparation worksheet for each route. |
| 11 | My Applications | Save/resume, export JSON/PDF, delete and explicitly citizen-marked submission status. |
| 12 | Service Centre Locator | Search local records by locality, PIN or district; time-stamped directories, contacts where verified and directions for address records. |
| 13 | Notifications | Opt-in match, missing-document and upcoming-deadline reminders; snooze/dismiss and periodic local jobs. |
| 14 | My Welfare Report | Local downloadable PDF including profile summary, results, source references, documents and next actions. |
| 15 | Manage Schemes | Search, draft/review/publish/archive, immutable version history, concurrency guard, structured rules, links and date validation. |
| 16 | RAG Knowledge Base | Local PDF/TXT/image import or approved official HTML import, extraction/preview, review, activation, deactivation, source conflicts, checksums, index jobs and retrieval inspection. |
| 17 | AI Agent Monitor | See task status, model availability, tool path, source references, decisions, latency and job errors. |
| 18 | Experiments & Testing | Bundled labelled profiles, editable question dataset, two prompt versions, model tag and retrieval depth. Matched baseline/RAG comparison with stored outputs and manual review. |
| 19 | Research & Analytics | Fixture agreement, retrieval hit rate, reviewed citations/claim support, time, feedback, task progress, category/state charts, JSON report and CSV metrics. |
| 20 | Audit Logs | Timestamped sanitized events; filters and export. Citizen data is excluded from the admin aggregate screen. |
| 21 | Privacy & Security | Cookie-bound household access and separate credentialed admin, consent, retention, private export/deletion, protected uploads and password rotation. |
| 22 | System Settings | Language/state list, model tags, loopback port, top-k, review age, health/disk/index, content backup/restore. Data and speech directories are configurable at launch. |

## Implementation map

* **Browser** — templates/index.html, static/style.css, core.js, citizen.js, admin.js, languages.js and start.js. Local font support for Telugu and Hindi. Bootstrap 5 assets are copied from the installed package by the launcher.
* **Web and orchestration** — FastAPI request schemas, cookie/role checks, scoped workflow commands, background maintenance, source and experiment jobs. Navigation is a bounded workflow; multiple specialist roles share a local model. Discovery filters, evidence retrieval, deterministic eligibility, document preparation, application validation and verification have distinct responsibilities.
* **Local persistence** — navigator/store.py initializes schema v1 transactionally. PyMySQL connects to the local MySQL service. Tables use parameterized queries and foreign-key cascades. The app uses a server-rendered HTML shell with Fetch interactions. Jinja2 and SQLAlchemy were suggested choices in the brief; the finished shell and MySQL layer do not require those abstractions.
* **Decision logic** — navigator/rules.py supports typed input, age and annual income units, AND/OR, exclusions, alternative routes, official-review cases and stale/missing sources. The simulator, citizen checks and tests call the same evaluator.
* **AI and operations** — navigator/ai.py handles the loopback model, versioned embedding cache, local Chroma, evidence ranking, citation checks and a second local support check. navigator/ops.py handles source versions, safe content restore and experiment execution. Indexing is idempotent by document identity and hash.
* **Scanner, speech and exports** — navigator/media.py handles bounded extraction, local OCR and dictation, reviewed fields and multi-page PDFs. Raw citizen scans remain temporary. Native browser voices must identify themselves as local.
