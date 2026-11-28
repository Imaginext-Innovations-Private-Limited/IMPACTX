# Evaluation on real cases

Put each case in `eval/cases/<case_id>/` with the bill files and a `label.json`
(format in `kk/evaluation.py`). Then run:

    python -m kk eval eval/cases

Only two kinds of case are accepted:

1. **consented_bill** – a real bill shared with written consent. Black out names, phone numbers,
   UHID and Aadhaar on the image before it is stored. Keep the signed consent form offline and
   record only its id in `label.json`.
2. **decided_case** – an overcharging case already decided by a consumer commission, NPPA or a
   state regulator. Enter only the bill lines quoted in the order, with the citation and URL.

Two people label every case independently and resolve disagreements before use; report the
agreement. Do not add generated or simulated cases. Do not commit personal data to git
(`eval/cases/` is ignored by default).

Ask your department whether collecting real bills needs approval from the university's
ethics committee before you start.
