Historical validation of the original eight-route release. For this edition see README_FIRST.txt and KARNATAKA_SOURCES.txt.

# Corpus and validation record

## What ships offline

The first-run catalogue contains **eight scheme routes and 22 source-linked passages**, current to the package review date of 24 November 2026. Most seed passages are curated summaries. Some include short excerpts in the issuing authority's original language. They are identified as such and include source title, issuing portal and page or section. The package does not contain complete copies of all government PDFs. Admins can ingest approved official originals, inspect extraction, approve chunks, and re-index locally. A full imported PDF is kept in the local content store and can be downloaded again by an admin. Seed URLs and original text are in seed/sources.json.

The portal is an academic assistance system. Authoritative enrolment, identity verification, application submission and final approval are performed by the issuing service. The portal shows the distinction between a possible match, document readiness and application-window status. Sources without reliable dates or current instructions direct the citizen to the responsible department. The catalogue includes one Telangana marriage-assistance entry with two official routes. It is a pilot covering the listed categories and schemes.

| Route | Official starting reference |
|---|---|
| PM Ujjwala | https://www.pmuy.gov.in/Ujjwala2.html |
| PM-KISAN | https://pmkisan.gov.in/ and the revised operational guidelines linked in the local catalogue |
| Ayushman Bharat 70+ | https://nha.gov.in/img/resources/English_FAQs_related_to_the_benefits_for_senior_citizens.pdf |
| NTR Bharosa old-age pension | https://sspensions.ap.gov.in/SSP/Home/About and the dated state orders, including the ST age exception requiring current verification |
| Kalyana Lakshmi / Shaadi Mubarak | https://telanganaepass.cgg.gov.in/KalyanaLakshmiLinks.jsp |
| National Means-cum-Merit Scholarship | Ministry of Education annual report and cycle notice at https://www.pib.gov.in/PressReleasePage.aspx?PRID=2295776 |
| PMAY-U 2.0 | https://pmay-urban.gov.in/uploads/guidelines/Operational-Guidelines-of-PMAY-U-2.pdf |
| PM Vishwakarma | Ministry of MSME CHAMPIONS FAQ in seed/sources.json and https://pmvishwakarma.gov.in/ |

The cached centre directory includes address records and directory links, labelled separately. Check the issuing directory before travelling. Source and review dates accompany each record.

## What was run during packaging

* Python 3.12 on Linux. FastAPI 0.141.1, Pydantic 2.13.4, Uvicorn 0.52.1, PyMuPDF 1.26.6 and Pillow 13.0.0 were available in the build environment.
* **11 automated test methods**, including an embedded suite of **33 labelled fictional eligibility cases** across the eight routes. Coverage includes exact age/income boundaries, an exclusion, a state mismatch, unclear answers, alternative criteria and the unconfirmed historical exception. The fixture labels are project-authored. They need independent subject-matter review before they can support a research accuracy claim.
* A consented citizen selected and changed profiles, screened, simulated, saved and resumed a draft, changed conditional document requirements, viewed and snoozed reminders, downloaded a readable PDF, exported and deleted a profile. Another browser session could not access it.
* Admin checks covered protected routes, draft/publish, stale-version rejection, PDF ingestion, duplicate detection, evidence activation/deactivation, content backup and transactional restoration. Invalid files and cross-origin state changes were rejected.
* A real image was processed by the installed English Tesseract binary; a separate real text PDF produced reviewable fields. Generated report PDFs were reopened and text checked.
* Local model adapter tests exercised generation/citation verification, unsupported-output fallback, embedding-cache reuse and paired research runs with **controlled responses**. These tests establish the application wiring. Live local model answer quality and inference speed were not measured in this environment.
* The clean package was extracted and started with a fresh data directory. Its live localhost HTTP API and static assets were checked. A JavaScript render harness exercised all **22** destinations against the live API. This was a template/route test; it did not measure browser layout.
* The environment could not launch its Chromium renderer because operating-system browser sockets were unavailable. A real-browser acceptance script is included for the target laptop. Windows/macOS execution, live Ollama/Chroma performance, microphone quality, and Telugu/Hindi speech/OCR require a target-device run. The bootstrap assets and optional native/model packages are installed on that device.

## Run checks on a laptop

Use CHECK_WINDOWS.bat after first setup. On Linux/macOS run `.venv/bin/python -m unittest discover -s tests -v`. Automated tests run on temporary databases and isolated fixtures. **Admin → AI experiments → Run labelled eligibility tests** is the interactive evaluation. Under the button, you can upload independently labelled fictional cases and choose the source review date for a reproducible run.

For optional browser testing, use the app's Python environment:

```sh
python -m pip install playwright
python -m playwright install chromium
python tests/browser_check.py
```

On a machine with an existing compatible Chromium installation, CHROMIUM_PATH can point to that executable. The browser script starts another copy of the server with a temporary local data directory. It checks all 22 sections, browser form interactions, desktop/mobile layout width, all three language selections, profile creation and draft persistence.

## Research procedure

1. Have an independent reviewer label fictional citizen profiles and each benchmark question's expected passage before running the evaluation. Document disputed or incomplete source clauses.
2. Record CPU, RAM, OS, exact model tags/digests/quantization, corpus hash, prompt version and retrieval top-k. The app records the selected model/settings, dataset hash, outputs and timing.
3. Run matched LLM-only and LLM+RAG questions. A retrieval-only fallback is visibly labelled and should be excluded from a generative comparison. Inspect each answer against its cited passage. Record whether its claims are supported, citations correct, or it contains an unsupported claim.
4. Include unsupported questions, source instructions that should be ignored, stale evidence, conflicting documents, missing data and application cycles with past deadlines. Compare native-language quality with a fluent reader and keep the original passage visible.
5. Export the results. Report sample size, denominator, failed runs and hardware limits alongside any percentages. Avoid extrapolating fixture agreement to all Indian welfare schemes.
