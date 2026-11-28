# Kharcha Kavach v4

Reads a real Indian hospital bill, matches each line to the official rule that governs it where
one exists (NPPA price caps, printed MRP, PM-JAY entitlements) on the date of treatment, says
plainly which lines had no rule to check, proves every rupee it shows, and drafts the complaint
for the right office. Screens, letters and a spoken summary in English, Hindi, Kannada,
Gujarati, Tamil and Telugu.

**Principle:** the language model reads and explains; rules decide; data proves.

- Every number on screen is a *Figure* with a role (billed, ceiling, excess…), an origin
  (bill, rule data, computed, user-confirmed) and evidence (bill crop, gazette row, formula).
- A language model can never put a digit on screen: it writes role-typed slots like
  `[excess:F31]`, which a verifier checks and code fills.
- Only binding rules produce a red "not allowed" finding. Benchmarks and voluntary standards
  are amber questions. Missing facts give grey "cannot verify", never a guess.
- Every result says how much of the bill a rule could check ("3 of 12 lines, 57.57% of the
  billed amount") and, for each line, what it was matched to and why, or why nothing applied.
- The challengeable amount is split by who decides it: the hospital (price caps, MRP,
  arithmetic) or the scheme (a grievance the State Health Agency decides, not an automatic refund).

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full architecture, workflow and module guide, and [docs/DEMO.md](docs/DEMO.md) for the 3-minute stage demo.


## See it in 60 seconds

[docs/demo.mp4](docs/demo.mp4): a stained photo where the app asks instead of guessing, a clean bill with
₹20,469.34 to challenge, the receipt for one rupee amount, the number guard, the phone-call script in Hindi,
one-tap send, and the proof card. Captions on screen, no sound needed.

## From finding to action

- **One-tap send:** each letter opens WhatsApp, email or SMS with the text filled in, and names the office it is for.
  Nothing is sent until the family presses send in their own app.
- **Proof card:** the browser draws one image (browsers join Indian-script letters on every OS; the server's `/api/audit/{sid}/proof-card.png` draws the same card, in English if Pillow has no text shaping, as on Windows) - 1080 px wide, with the disputed line, the billed amount,
  the most the rule allows, the excess and a QR code to the official order. The hospital name is masked. Six languages.
- **What to say on the phone:** a short script for the hospital billing desk and, for scheme cases, the PM-JAY helpline 14555,
  built from the bill's own figures, shown and read aloud.
- **What a scheme could have paid:** for a bill paid in cash, the panel shows how much PM-JAY, Vay Vandana,
  the family's state scheme (all 36 states and UTs) or a job-linked scheme (ESIC, CGHS, ECHS, CAPF) could have paid,
  with eligibility, the eligibility-check link and helpline, and the official source for every cover. It is awareness
  only and is never added to the amount the family can challenge.
- **Send to family:** shares the letter and the proof card through the phone's share sheet, or WhatsApp.
- **GST charged where it shouldn't be (rule TAX-GST):** treatment by a hospital is exempt from GST (CBIC Circular
  32/06/2018-GST); from 18.07.2022 only a non-ICU room above ₹5,000 a day carries GST, at 5% (Notifications 03/2022 and
  04/2022-CT(Rate)). GST added to doctors, procedures, tests, ICU, cheaper rooms or a patient's diet is red; a CGST/SGST
  line on an in-patient bill is red for the part the rooms do not allow; GST added on medicines of an admitted patient
  is amber (a question, never a claimed amount); cosmetic surgery is grey.
- **Complaint tracker:** under every letter, the family notes the day they sent it. The tracker shows when a reply is
  due, the last day to go further and the next office, for the hospital, NPPA, PM-JAY (NHA's 15/30/30-day rules),
  the insurer (IRDAI's two weeks, then Bima Bharosa, then the Ombudsman within one year) and the consumer
  commission (two years, s.69 Consumer Protection Act). Each day count opens its source; where no official reply time
  exists the wait is labelled as our suggestion. "Add reminders to my calendar" downloads an .ics file. Dates stay in
  the browser.
- **Insurance deduction check:** the family types each cut from the insurer's settlement letter. Each is matched to
  IRDAI's standard lists (146 items: List I optional, II-IV part of room, procedure or treatment charges). Optional
  items need an add-on; subsumed items should not be billed by a network hospital in a cashless claim (ask the hospital
  to remove them); anything not on the lists, or cut in proportion to room rent from ICU, medicines, implants or tests,
  goes to the insurer with the rule to cite. Questions only, never a claimed amount.

## What changed after review

| Concern | What the code does now | Where |
|---|---|---|
| "Checks every line" overclaimed | Coverage on every result; per-line match reason or "no official limit loaded" | `kk/rules/crosswalk.py`, coverage panel |
| Bill text → rule mapping not shown | Crosswalk with matched words, rule row and source; brand table from hospital-published stent lists; evaluated on 67 hospital strings | `data/reference/stent_brands.csv`, `eval/crosswalk/REPORT.md` |
| GST formula unproven | NPPA wording stored with the source ("exclusive of Goods and Services Tax as applicable"; knee "excluding taxes, if any"), shown in every cap's proof; CARE Hospitals' list confirms ceiling + 5% GST | `data/sources.yaml` (`tax_quote`) |
| "Possible refund" overstated | "Amount you can challenge", split into hospital refund vs scheme grievance, plus the price-cap fallback | `engine._by_remedy`, `remedy_*` messages |
| No real-user evidence | Pilot protocol, consent forms (en/hi/kn), anonymiser, case log, outreach plan. No evidence is claimed until it exists | `pilot/`, `scripts/anonymise_bill.py` |

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # Tesseract (apt install tesseract-ocr) is optional, used as a second OCR reader
python -m pytest -q                      # 209 tests
python scripts/preflight.py              # stage check + offline backups (see docs/DEMO.md)
python -m kk kb check                    # which rules have their data loaded (12 of 14 out of the box)
python scripts/eval_crosswalk.py         # line-matching on hospital-published text
python -m kk kb check                    # validate the knowledge base
python -m kk serve                       # open http://127.0.0.1:8000 on a phone or laptop
```

Command line:

```bash
python -m kk audit bill_page1.jpg bill_page2.jpg --payer cash --state karnataka --lang kn --out report.html
python -m kk audit bill.pdf --payer pmjay --hospital-empanelled yes --patient-paid yes --lang hi
```

### Explainer chat (six languages)

The result screen has a chat panel. Families tap a suggested question ("Will I get the money
back?", "Why this charge: Xience Alpine?") or type or speak their own, in any of the six
languages. Answers are built from this bill's findings, its figures (tappable for proof), the
official helpline numbers in `data/channels.yaml` and reviewed sentences; medical and legal
questions are refused with a pointer to the right person. If a local model is running it may
reword an answer, but only through the same slot verifier. Answers can be read aloud.
`GET/POST /api/audit/{id}/chat`, `GET /api/audit/{id}/chat/{n}/audio`.

### Spoken summary (six languages)

The result screen has a Listen player. It reads a short summary aloud in English, Hindi, Kannada,
Gujarati, Tamil or Telugu, with captions that highlight as it speaks. Numbers are said from the
same stored figures the screen shows (English in lakh/crore words, Indian languages as native
numbers with the rupee word); digits in item names such as "3.0x28" are never spoken.
The phone's own voice is used when it has one for the language; otherwise the server speaks:

For each language the server uses the first voice that works:

| Backend | Languages | Notes |
|---|---|---|
| Bhashini | all six | natural; needs `KK_BHASHINI_USER_ID`, `KK_BHASHINI_API_KEY`, internet; not tested here without keys |
| Neural (sherpa-onnx) | English, Hindi, Gujarati | natural, offline after `pip install sherpa-onnx==1.12.40` and `python scripts/fetch_voices.py`; Hindi voice is CC BY-NC-SA 4.0 |
| Edge online voices | all six | natural Microsoft neural voices (`kn-IN-SapnaNeural`, `ta-IN-PallaviNeural`, `te-IN-ShrutiNeural`, ...); `pip install edge-tts` (in requirements); needs internet, no account; on by default, `KK_TTS_ONLINE=0` turns it off. This is what makes Kannada, Tamil and Telugu speak on Chrome for Windows, which has no voice for them |
| gTTS | all six | natural; needs internet; opt in with `KK_TTS_GTTS=1` and `pip install gTTS`; not testable here |
| espeak-ng | all six | offline but robotic; last resort |

When the server has a natural voice for a language it is preferred over the device's voice.
If the server voice fails (for example, no internet for the online voice), the app falls back to the device's voice.
On a laptop with no internet, Kannada, Tamil and Telugu still work in Microsoft Edge (its own voices) or on an Android phone.
English item names are not read inside Indian-language speech (they stay in the captions).

`GET /api/audit/{id}/voice?lang=ta` returns the script; `GET /api/audit/{id}/voice.audio?lang=ta` the audio.
Indic fonts are bundled (`kk/web/fonts`, SIL OFL), so text renders offline.

Optional plain-language explanations use a local model through Ollama
(`ollama pull qwen2.5:7b-instruct`; set `KK_OLLAMA_MODEL` to change). Without it, the
fixed templates are used. Correctness never depends on the model.

## What data is included, and what you must load

Only values verified against official notifications ship in `data/reference/`:

| Table | Content | Source |
| --- | --- | --- |
| `stent_ceilings.csv` | BMS ₹10,762.15, DES ₹39,186.03 (ex-GST), 1 Apr 2026 – 31 Mar 2027 | NPPA notification 25 Mar 2026 |
| `knee_implant_ceilings.csv` | 15 component ceilings, 16 Sep 2024 – 15 Jan 2027 | S.O. 3869(E), extended by S.O. 4171(E), 5190(E), 6222(E) |
| `gst_rates.csv` | Medical devices and medicines 5% from 22 Sep 2025 | 56th GST Council decisions |

Load the rest from official PDFs before a real deployment (the importers stage rows; a named
person approves them after checking each row against the PDF):

```bash
python -m kk kb import-nppa ceiling_notification.pdf --source-id nppa_scheduled_ceilings --valid-from 2026-04-01 --valid-to 2027-03-31
python -m kk kb import-hbp hbp2022_state_copy.pdf --source-id hbp_2022 --valid-from 2022-04-01
python -m kk kb import-empanelment karnataka_hospitals.csv --source-id pmjay_empanelment --status-from 2026-11-01
python -m kk kb approve data/staged/<file>.csv --table <table> --reviewer "Your Name" --yes
```

The loader refuses any row without a registered source, a page/row reference and a valid date
range. Every rule has validity dates, so an old bill is judged by the rule in force then; a date
with no loaded rule gives "cannot verify". Run `python scripts/refresh.py` daily to watch the
official pages and flag rules close to expiry.

Before launch, replace the secondary links in `data/sources.yaml` (news reports, hospital
price lists) with the official PDFs, and have native speakers review the Hindi, Kannada and
Gujarati text in `kk/compose/messages_*.py` and `kk/web/app.js`.

## Rules

| Family | Rules | Verdict |
| --- | --- | --- |
| Price | Stent, knee implant, scheduled medicine (after unit confirmation), MRP | Red |
| Entitlement | Covered item billed to a scheme beneficiary; card holder treated as cash | Red (scheme channel) |
| Arithmetic | Quantity × rate ≠ amount | Red (hospital desk) |
| Arithmetic | Printed total ≠ sum of lines | Amber |
| Tax | GST on exempt treatment, ICU, rooms up to ₹5,000 a day, patient diet; CGST/SGST lines beyond what rooms allow | Red (hospital desk); amber for medicines and mixed bills; grey for cosmetic work |
| Convention | Duplicates, room days > nights + 1, item dated outside the stay | Amber |
| Format / rights | Missing quantity, rate, batch, expiry (IS 19493, voluntary); bill not itemised (Patients' Rights Charter) | Amber |
| State | Karnataka disclosure circular (on hold in the High Court) | Info |

Rules live in `data/rules.yaml`; the checks are in `kk/rules/`. One line's recoverable amount
is its largest red claim, never the sum of overlapping claims. Unclear stent types or implant
materials use the highest candidate ceiling, so a finding can only understate.

## Test bills (fictional, for testing the code only)

`tests/fixtures/sample_bills/` holds five fictional bills, each marked "TEST BILL - NOT A REAL
PATIENT", that between them trigger every rule. Each has a `.json` with the typed-in version,
the answers to the app's questions and the hand-worked expected results.
`tests/test_sample_bills.py` runs each bill from the document (PDF, or OCR for the photo) and from
the typed-in version. Regenerate with `python tests/fixtures/sample_bills/make_bills.py`.

| Bill | Situation | What it exercises |
| --- | --- | --- |
| `bill1_cardiac_cash.pdf` | Cash patient, Karnataka | Stent caps (known and unknown type), MRP, quantity × rate, duplicate, room days, item outside stay, missing expiry, total mismatch, Karnataka note, skipped advance/net rows |
| `bill2_knee_pmjay.pdf` | Ayushman card, empanelled, patient paid, Gujarat | Knee-implant caps, scheme entitlement on every covered line, room upgrade and attendant charges as questions, no double counting |
| `bill3_interim_photo.jpg` | Ayushman card treated as cash, March 2026, phone photo | OCR path, cash denial, lump-sum package (not itemised), no rule data for that date |
| `bill5_outlier_extremes.pdf` | Cash, extreme values | 24× stent price, misplaced zero, 45 ICU days for 2 nights, a 1-crore total, zero and negative lines |
| `bill6_gst_on_treatment.pdf` | Cash, medical admission | CGST + SGST of ₹4,518 added to a bill whose rooms are ICU or ₹3,500 a day: all of it flagged (TAX-GST) |

These are never used as accuracy data.

## Evaluation on real cases only

See `eval/README.md`. Cases are consented real bills (de-identified) or overcharging cases
already decided by a consumer commission or regulator. No generated or simulated cases.
The unit tests in `tests/` use small hand-built inputs to check logic; they are not accuracy data.

```bash
python -m kk eval eval/cases
```

## Layout

```
kk/
  extraction/   preprocess (deskew, perspective), OCR ensemble (RapidOCR + Tesseract, PDF text layer),
                table reconstruction, parsing with word-level provenance, arithmetic validation
  kb/           knowledge base loader (strict) and importers (NPPA, HBP 2022, empanelment)
  context.py    hospital, empanelment on the date, payer, scheme booking, date, package
  rules/        price, entitlement, arithmetic, convention, format, state; engine with aggregation
  figures.py    the figure store
  compose/      templates in 6 languages, renderer, slot verifier, optional LLM explainer, slot-safe translation
  grievance.py  channel routing and letters        report.py  self-contained HTML report
  guard.py      Aadhaar (Verhoeff) / phone / ID masking, injected-text removal, refusals, language detection
  matching.py   treatment words -> HBP 2022 procedures (BM25 on character 3-grams)
  voice/        spoken summary: script from figures, number words, espeak-ng / Bhashini speech
  service.py    audit sessions (memory only, 24-hour expiry)   api.py  FastAPI + mobile web app (kk/web)
data/           sources.yaml, rules.yaml, channels.yaml, watch.yaml, reference/*.csv
scripts/        refresh.py (daily watcher), eval_crosswalk.py, anonymise_bill.py
pilot/          protocol, consent forms, case log, outreach
eval/           evaluation instructions; cases/ is git-ignored
tests/          pytest
```

### Scheduled-medicine ceilings (real NPPA data, reviewed before use)

`data/staged/nppa_so1581_2026_scheduled.csv` holds 20 rows of NPPA order S.O. 1581(E) (Gazette of India No. 1516, 25 March 2026, in force from 1 April 2026): sodium chloride 0.9%, Ringer lactate, paracetamol injection, tramadol injection and diclofenac capsule. Check them against the Gazette PDF, then load them:

```bash
python -m kk kb approve data/staged/nppa_so1581_2026_scheduled.csv --table nppa_scheduled_ceilings --reviewer "Your Name" --yes
python -m kk audit tests/fixtures/medicine_bill/medicines_cash.json
```

Until then PRC-SCHED does not run, and `kk kb check` and `/api/health` say so.

## Real public data

| Source | What it is | How it is used |
|---|---|---|
| Hospital stent and implant price lists (Apollo, Breach Candy, Fortis, CARE, Ruby Hall) | Brand and component names as hospitals print them | Brand table and `eval/crosswalk/` (67 + 8 strings) |
| Hugging Face `shaluyadav/newdatafiles` | 776 labelled bill pages (item, qty, rate, amount); images not included; no licence stated | `scripts/eval_public_lines.py` downloads it on your machine and checks line matching and the arithmetic rule; nothing is redistributed |
| GitHub `johnny0213/Complex-Table-Extraction` | Checked: a handful of Chinese medical bill images (Apache-2.0), not Indian bills | Not used |
| Consumer commission orders, news reports | Itemised bill scans published as evidence or in reporting | `scripts/eval_ocr_images.py` scores bill reading on images you collect, after `anonymise_bill.py` |

How the three test bills were built, line by line, is in `tests/fixtures/sample_bills/PROVENANCE.md`.
What the real lines changed: a line whose amount exceeds quantity × rate by exactly a standard
GST rate is now amber ("may include tax"), not red.

## Pilot

`pilot/README.md` is the protocol for real evidence: consent, anonymising with
`scripts/anonymise_bill.py`, two-person labels, and what to report. Nothing is claimed yet.

## Limits (stated to users)

Lines with no official price limit loaded (most consumables, procedures, nursing, doctor fees,
and medicines outside the loaded NPPA list) get only arithmetic, duplicate and date checks, and
the result says so. Room, doctor and procedure fees for cash patients are mostly not price-regulated nationally,
so they are only compared with CGHS/HBP rates (amber). Non-scheduled medicines are checked
against MRP only. Scheme card status comes from the user. Handwritten or damaged bills give
grey lines. Nothing here is legal or medical advice; the hospital or an authority decides.
