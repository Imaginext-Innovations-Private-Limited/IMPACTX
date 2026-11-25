# 4-minute judge demonstration — ScamShield AI

**0:00–0:30 — Problem:** “Victims face urgent threats and payment requests across SMS, calls and WhatsApp. They're unsure whether to trust or report. We make the warning signs visible before they act.”

**0:30–1:00 — Product overview:** Open http://127.0.0.1:8000. Show user-supplied text, screenshot, and permissioned microphone. Emphasize that this is **real-time analysis of typed/pasted input**, *not* automatic phone interception.

**1:00–1:45 — Digital arrest:** Click the Digital Arrest sample. Show matched evidence (authority claim, arrest language, payment demand) and practical safety actions.

**1:45–2:15 — UPI:** Click UPI Scam. Point out “UPI PIN requested to receive money,” and explain why users should never enter a PIN for receiving funds.

**2:15–2:45 — False positive check:** Click Normal Message. The app should avoid calling it fraudulent. Note that “no clear signal” is not proof of safety.

**2:45–3:15 — Screenshot / voice:** Upload a prepared SMS screenshot and review OCR; optionally use microphone if supported. Keep a fallback live demo using paste if OCR or speech is unavailable.

**3:15–3:40 — Engineering architecture:** FastAPI, local rule-based screening, small synthetic-trained text classifier, Tesseract OCR, explainable signals. Explain why there's no accuracy figure based on synthetic examples.

**3:40–4:00 — Safety and next steps:** Open reporting links; explain 1930. Show the automated test run and README. The product does **not** submit reports on a user's behalf.

## Live demo reliability checklist

- `python -m pytest tests -v -s` passes on demo laptop
- Project launches with `run.bat`, no external secret needed
- Visit `/api/health` and get status `ok`
- Have five example messages preloaded
- Have screenshot backup with clear large text; OCR test on actual demo laptop
- Keep internet optional for core analysis; external government portals naturally require connectivity
- GitHub repo visibility/permission and commit history verified
- 4 team members can explain their own modules and tradeoffs

## v1.3 differentiator

Switch the same digital-arrest example from English to Odia, then switch to UPI fraud in Odia. Explain that the engine selects a different approved script for the detected type, and the speech provider receives only that fixed script. Generate and test audio before evaluation; cached clips can be played offline. Show a normal payment reminder and the uncertainty disclaimer. Do not claim Odia audio or regional language accuracy unless the team has actually verified them. Explain the trade-off: bounded templates are safer and cheaper than arbitrary generated speech, but only cover a fixed list of categories and one primary type per assessment.

**Current release:** see the project README for v2.0 startup. For recorded-audio demo, use Voice → select a consented synthetic recording → Transcribe recording → review transcript → Analyze. Distinguish cloud STT from fixed-template TTS and avoid claiming live call interception.


## v1.5 add-on (30 seconds)
Select Odia (or any language) and press **Hear warning**: it speaks even with no browser voice, internet or key. Say: "The app does not depend on the judges' browser. We ship the audio and fonts with it, and fall back automatically if a browser voice fails."
