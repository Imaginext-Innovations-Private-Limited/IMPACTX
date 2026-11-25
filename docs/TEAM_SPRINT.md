# Three-day four-person sprint plan

## Deliverable definition (acceptance criteria)
- Fully launchable on a Windows laptop with `run.bat`.
- Five demo scenarios available and results are visibly distinct.
- Text/UPI scan takes user input and returns matched indicators with quoted evidence.
- Screenshot upload extracts text with Tesseract; an OCR failure is visibly reported.
- English and Hindi summary options available; voice transcription explicitly optional.
- Official links to cybercrime.gov.in and Sanchar Saathi and 1930 visible.
- `python -m pytest tests -v -s` passes with zero regression.
- Public GitHub repo has clear README, license, sample screenshots and four actual contributors (add only genuine commits and contributors).

## Team responsibilities

| Role | Owns | Proof for evaluators |
|---|---|---|
| 1. Detection & research | `scamshield/engine.py`, signal definitions, independent labeled examples | Shows false positives and clear limitations |
| 2. Backend & OCR | `scamshield/main.py`, OCR installation and validation | Demonstrates APIs, upload handling and errors |
| 3. Frontend & accessibility | `static/`, responsive UI, Hindi output, microphone demo | Shows user journey on mobile/desktop |
| 4. QA, integration & presentation | `tests/`, end-to-end testing, GitHub, README and demo script | Shows test logs and repeatable setup |

## Timing

**23 November:** Download, run, review architecture together; each teammate gets own branch; test scenarios 1–5.

**24 November:** Perform real-device integration and UX review; add separately sourced labeled test examples and document failures.

**25 November:** Fix highest-severity failures; freeze features; confirm screenshot OCR, browser access, tests, GitHub, rehearsal; ensure local offline demonstration fallback.

**26 November, before 8:45 AM:** Verify launch, sample image, key scenarios, test command and laptop power/internet. Demo only verified functionality.

## GitHub publish steps

Create an empty GitHub repository, then from this project root:

```bash
git init
git add .
git commit -m "Initial working ScamShield AI hackathon MVP"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/scamshield-ai.git
git push -u origin main
```

Replace `YOUR_USERNAME` with the repo owner. Do not claim collaboration without teammates' actual changes. Avoid committing real banking messages or identifiable screenshots.


### v1.2 multilingual responsibilities before demo

- Bengali/Hindi speaker: check pronunciation and plain-language warnings. Test legitimate OTP SMS vs coercive fraud examples.
- Kannada/Telugu speaker: check each warning script, record at least high/caution if native TTS is missing, listen and correct pronunciation.
- Odia speaker: check natural wording; record Odia voice clips if no suitable system/browser voice is installed (likely on many PCs).
- Fourth teammate: run `python -m pytest tests -v -s`, test clips, permission prompts and responsive UI, update the README and GitHub demo limitations.
- **Acceptance:** Every claimed audio language must audibly work on the actual demo laptop. If a language does not have TTS or a recorded clip, clearly label its spoken-warning feature not yet available.
