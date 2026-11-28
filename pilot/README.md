# Pilot: getting real evidence

The test bills in `tests/fixtures/sample_bills/` prove that the code does what it says. They do not
prove that it helps anyone. This folder is the plan for collecting that evidence, and nothing
here may be skipped or simulated.

## What counts as evidence

| Kind | What it is | Where it goes |
|---|---|---|
| Consented bill | A real hospital bill a patient or family shares with written consent, anonymised with `scripts/anonymise_bill.py` and checked by eye | `eval/cases/<id>/` with `origin: consented_bill` |
| Decided case | An overcharging case already decided by a consumer commission, NPPA or a State Health Agency, with the bill lines quoted in the order | `eval/cases/<id>/` with `origin: decided_case` and the citation URL |
| Field note | What a help-desk worker, Arogya Mitra or NGO volunteer said after using the app on a real bill (no patient data) | `pilot/field_notes.md` |

Hospital price lists (stent and implant lists that hospitals publish under the NPPA display
requirement) are already used for the line-matching evaluation in `eval/crosswalk/`.

## Before the first bill

1. Ask your project guide whether the university ethics committee must approve this. Do not
   start until you have that answer in writing.
2. Print the consent form (`consent_form_en.md`, `_hi.md`, `_kn.md`). Read it aloud if the person
   prefers. Keep signed forms offline, never in git, and give each one an id such as C-0001.
3. Agree with a second person who will label every case independently.

## For each bill

1. Get consent. Photograph or scan the bill pages on your own phone.
2. Run `python scripts/anonymise_bill.py page1.jpg page2.jpg --case-id KK-0001 --consent-id C-0001 --out eval/cases/KK-0001`.
3. Open every `review-N.png`. If anything personal is still readable (name, phone, address, UHID,
   Aadhaar, ABHA, signature, photo), delete the case folder. Otherwise delete the review images.
4. Delete the original photos from your phone.
5. Two people fill in `label.json` separately (`lines` and `expected`), compare, and record what
   they disagreed on in `agreement_notes`.
6. Run `python -m kk eval eval/cases` and record the result in `case_log.csv`.

## What to report (and how)

- Number of real bills, where they came from (type of hospital, state), and the date range.
- Line-matching coverage: lines matched to a rule ÷ all lines, and the share of the billed amount.
- Reading accuracy: amounts read correctly by OCR, before and after the person confirmed lines.
- Rule accuracy against the two-person labels: red findings that were right, missed, or wrong.
- Remedy outcomes, only when the family tells you: asked the hospital, filed a grievance, refund
  received (amount and how long it took). Never estimate outcomes you did not observe.
- Report small numbers as they are ("7 bills, 2 with a binding-rule overcharge"). Do not
  extrapolate to India.

`case_log.csv` has the columns for this.
