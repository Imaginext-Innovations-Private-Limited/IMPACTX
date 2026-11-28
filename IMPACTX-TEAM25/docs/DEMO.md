# Kharcha Kavach - 3-minute stage demo

One flow, shown reliably: **bill -> red finding -> receipt -> number guard -> letter and voice**.
Everything else (chat, six languages, importers, CLI, watcher) stays off stage unless a judge asks.

## The pitch (say this first, 20 seconds)

> Hospital bills overcharge families, and nobody can prove which line is wrong.
> Kharcha Kavach reads the bill, applies the official rules in force on the bill's date, and gives
> every rupee a receipt back to the bill or the government order. Then it hands the family the
> letter, the proof card and the words to say on the phone.

Say "test bill" plainly: *"This is our test bill. Every price limit on it is the real NPPA ceiling."*
If you have a real, anonymised bill with consent, use it instead and say so.

## Before you go on stage (one hour before)

1. `python scripts/preflight.py --lang hi` -> all checks must say PASS or WARN.
   It also saves offline backups in `demo_assets/` (Hindi MP3s, proof card, printable report, letters).
2. `python -m uvicorn kk.api:app --port 8000`, then open **`http://localhost:8000/?demo=1`**.
   Demo mode hides the chat, shows English, Hindi and Kannada, and adds one-click test bills.
3. Keep `tests/fixtures/demo/bill3_stained_photo.jpg` and `tests/fixtures/sample_bills/bill1_cardiac_cash.pdf` on the desktop.
4. Keep `demo_assets/` open in a background window. Turn the volume up; switch off notifications.
5. Optional: put the laptop in airplane mode before you start. Nothing in this flow needs the internet.

## Run of show (3 minutes)

| Time | Do | Say |
|---|---|---|
| 0:00-0:20 | Pitch (above), on the "problem" slide. | One stent billed Rs 58,000; the most the hospital may charge is Rs 41,145.33. |
| 0:20-0:45 | Switch to the app. Upload `bill3_stained_photo.jpg`, choose **Cash, self-paid**, **Karnataka**, **Check my bill**. The app shows the stained crop and asks about the stent line. Type **52000**, confirm. | Most tools guess. We refuse. A stain covers this number, so the app shows you the crop and asks. It never guesses an amount. |
| 0:45-1:00 | Back to the first screen, tap **Test bills: 1 - Stent, cash** (or upload `bill1_cardiac_cash.pdf`). Point at **Rs 20,469.34 you can challenge**. | A clean bill now. This is money the hospital itself must correct. |
| 1:00-1:25 | **Findings** -> stent card -> tap **Rs 16,854.67**. Walk the receipt: billed Rs 58,000 -> NPPA ceiling Rs 39,186.03 (row and date) -> GST 5% -> allowed Rs 41,145.33 -> excess. | Every number has a receipt. Nothing here was typed by an AI. |
| 1:25-1:45 | **AI explanation** tab -> **Try to fool the number guard**. Tap the Rs 25,000 example: **Blocked**. Tap the slot example: it fills Rs 16,854.67. | Every AI sentence must pass this check, in six languages. A model cannot slip a number past it. |
| 1:45-2:30 | Switch to **Hindi**. **Next steps** tab. Under **What to say on the phone**, press **Listen** for 10 seconds. Then on the NPPA letter press **WhatsApp** (show the filled message, do not send). On the stent finding, press **Share proof card**. | From bill to complaint in under two minutes: the letter for the right office, a card the family can forward, and the exact words for the phone call, in their language. |
| 2:30-2:45 | Scroll to **What could be checked**. | It shows which lines were checked by a binding rule and which got the basic checks. |
| 2:45-3:00 | Deck, closing slide. | Every rupee it flags, traced to the rule that governs it. |

## If a judge asks for more (have these ready, do not show unprompted)

| Ask | Show |
|---|---|
| PM-JAY / scheme case | Tap **Test bills: 2 - Knee, PM-JAY** (or upload `bill2_knee_pmjay.pdf` with PM-JAY, Gujarat, empanelled: yes, patient paid: yes). Each scheme finding shows its **Official basis**: NHA Operation Manual (April 2022), Annexure-1 Don'ts: *"Charge from the beneficiaries in any form as the benefit package includes the entire cost of treatment"*, and the Adhikar Patra: *"Free medicines, drugs, implants and food during the treatment"*. |
| A bad photo | Upload `tests/fixtures/demo/bill3_stained_photo.jpg`. A stain covers the stent rate; the app shows the crop and asks the user to confirm instead of guessing. Type 52000 and it continues. |
| Medicine price caps | `python -m kk kb check` shows PRC-SCHED waiting for review. Approve the 20 staged rows of NPPA S.O. 1581(E), then `python -m kk audit tests/fixtures/medicine_bill/medicines_cash.json`: 4 red lines, Rs 525.92. |
| Tests | `python -m pytest -q` (about 15 seconds). |
| Tamil or Telugu | Remove `?demo=1`, switch language. Say plainly that Indian-language text still needs native-speaker review. |
| More detail | `docs/ARCHITECTURE.md`, section 12 has the answer to each review question. |

## If something breaks

| Problem | Fallback |
|---|---|
| PDF upload slow or fails | Tap **Test bills: 1 - Stent, cash** at the top of the first screen (demo mode only). Same bill, same numbers, already typed; say so. |
| No sound / voice fails | Play `demo_assets/summary_bill1_hi.mp3` or `demo_assets/call_hospital_bill1_hi.mp3`; the text is on screen anyway. |
| Browser or server crashes | Open `demo_assets/report_bill1_hi.html`: findings, receipts and letters, offline. |
| Ollama question | It is optional. Without it, templates are used and the demo is identical. |
| Wi-Fi | Nothing in the stage flow needs the internet. WhatsApp only opens if the phone or laptop has it. |
| WhatsApp not installed on the laptop | Show the proof card and the call script instead; or run the app on your phone over the same Wi-Fi. |

## What not to show on stage

The chat, all six languages, the importer and reviewer step, the CLI, the daily watcher, the Karnataka on-hold rule,
the TTS backend chain. They exist; mention them in one line if asked. The soul of the demo is the receipt, the
number guard, coverage and the remedy split.

## Extra sample: coffee-stained photo of test bill 1

`tests/fixtures/demo/bill1_stained_photo.jpg` is test bill 1 photographed with a coffee stain
over the stent amounts, a slight tilt and uneven light (made with `scripts/stain_photo.py`).
Upload it with payer Cash and state Karnataka:

- both stents are still red (run-together OCR words such as "DrugElutingStent" are split);
- the guide-wire line (2 x 3,500 billed as 7,500) is asked about first, because on a photo a
  wrong sum may be a misread: amount to challenge 19,969.34 until it is confirmed, then
  20,469.34, the same as the PDF;
- the scheme panel shows 1,80,785 that a scheme card could have paid.

Make your own: `python scripts/stain_photo.py page.png out.jpg --box x0,y0,x1,y1`.

## Extra sample: handwritten C-section bill (TEST BILL 4)

`tests/fixtures/handwritten/bill4_csection_handwritten.jpg` is a printed bill-book page from a
fictional nursing home, filled in by hand in blue ballpoint for a caesarean (LSCS) delivery
and photographed. Made with `tests/fixtures/handwritten/make_handwritten.py` (Kalam font, OFL).
Upload it with payer Cash and state Karnataka:

- all 11 lines are read; handwritten 5, 0 and 1 read as S, o and I are repaired, and every
  repaired or unreadable number is asked about (Nursing: amount unreadable, type 1,500);
- after confirming: Ceftriaxone 6 x 85 written as 610 (100 to challenge), and 5 room days
  for a 3-night stay (ask how they were counted);
- with the NPPA S.O. 1581(E) rows approved and units confirmed, Ringer Lactate and Diclofenac
  are also over the ceiling: 497.35 in all;
- the scheme panel shows that a card could have paid the whole 54,780.

## Extra sample: outlier bill with extreme values (TEST BILL 5)

`tests/fixtures/sample_bills/bill5_outlier_extremes.pdf`, payer Cash, state Karnataka:

- red: stent 9,85,000 vs cap 41,145.33; injection 52,000 vs MRP 455; balloon 1 x 9,800 billed
  98,000. Amount to challenge 10,83,599.67;
- amber: 45 ICU days for 2 nights; a CT scan dated 2024; a 1 crore total against 28,06,875.03
  of lines;
- read exactly as printed: a 0.00 line, a 0.03 line and a -2,275 return line;
- not flagged (no official rule sets a limit): 12 stents, 10,000 tablets.

## Extra sample: GST on treatment (TEST BILL 6)

`tests/fixtures/sample_bills/bill6_gst_on_treatment.pdf`, or the "3 · GST on treatment" button with `?demo=1`.
Payer Cash. The hospital adds CGST 9% and SGST 9% (2,259 + 2,259) to a medical admission.
The rooms are an ICU (exempt whatever it costs) and a twin room at 3,500 a day (not above 5,000),
and treatment is exempt, so all 4,518 is flagged red (TAX-GST). Tap the 5,000 to open
Notification 04/2022-CT(Rate).

## Extra: complaint tracker and insurance deductions

- Next steps tab, any letter, "Track this complaint": enter the date the letter was sent. The step
  turns amber after its wait, the next office lights up, and "Add reminders to my calendar"
  downloads an .ics file. Tap a day count to see its source (IRDAI, NHA, the Consumer Protection
  Act) or the label "suggested".
- Next steps tab, "Insurance deductions": type `Gloves 350 Non-payable`, `Admission kit 500 NME`
  and `Coronary stent 12000 Proportionate deduction`, choose "cashless: yes", and check. Gloves:
  optional item (List I); admission kit: part of room charges, ask the hospital to remove it
  (List II); stent: a proportionate cut on an implant, which IRDAI's norms bar.

## Voice in Kannada, Tamil and Telugu

`pip install -r requirements.txt` installs edge-tts. With internet, the server speaks all three in
natural voices. Without internet, open the app in Microsoft Edge or on an Android phone, which have
their own voices for these languages.
