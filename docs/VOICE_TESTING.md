# v1.2 — Native speaker review and audio QA checklist

## Why voice-first, not text-only?
A person may understand spoken Bengali, Hindi, Kannada, Telugu, or Odia but be uncomfortable reading the language's script. ScamShield keeps the familiar English navigation for the initial hackathon, provides a spoken warning in the chosen language when a matching voice or local clip exists, and shows the text as a fallback. This is a prototype; consider icon-only controls and fully localized navigation in later work.

## Fast path on Windows
1. Start `run.bat` and open `http://127.0.0.1:8000`.
2. Try **Digital arrest**; choose a warning language. After analysis, the warning panel says either **Ready** or **No ... voice installed or recorded clip**.
3. Click **Hear warning** only when ready. It speaks *only a predefined warning*, not the user input or extracted evidence.
4. If a voice is missing, use native-speaker clips. Open `http://127.0.0.1:8000/static/voice-studio.html` in Chrome/Edge. Choose the language and warning type, start recording, speak the safety message naturally, and click Stop & download.
5. Put the downloaded files in: `static/voices/bn/high.webm`, `static/voices/hi/high.webm`, `static/voices/kn/high.webm`, `static/voices/te/high.webm`, `static/voices/or/high.webm`, etc. Use the exact `high`, `caution`, `review`, `no_clear_signal`, and `unknown` names. Supported formats are `.webm`, `.mp3` and `.m4a`. Refresh the main app and try again.
6. Native speakers must check every script. Make recordings in a quiet space; test actual playback before the hackathon. Confirm speaker consent before distributing voice recordings or committing them to GitHub. No real customer data belongs in these clips.

## Acceptance checklist for each language
- A complete digital-arrest scam is flagged, an ordinary classroom SMS is not, and a standard **do not share OTP** notice is not flagged as high risk.
- The listener understands the main instruction: don't send money, don't reveal OTP/PIN, and verify independently.
- The audio uses the selected language, pronounces the warning and 1930 clearly, and does not unexpectedly switch to English.
- The warning can be stopped and replayed; it stops when the language changes or the user clears the scan.
- Unavailable voices are shown as unavailable; the app never claims they are working merely because the selector exists.

## Known limitations to disclose to judges
- Browser speech engines vary by OS and installed voice; some language voices may be unavailable, especially Odia. The volunteer recordings provide a local alternative.
- Browser dictation is not the same as monitoring a telephone call. It may use a cloud service run by the browser vendor and may not support every regional language.
- Tesseract OCR is configured for English/Hindi only. Additional trained data and language-selection logic would be needed to OCR Bengali/Kannada/Telugu/Odia screenshots.
- The five-language translations and the regional keyword patterns are draft work; team review is required. The ML classifier is trained on synthetic data, not a representative independent multilingual fraud dataset. Avoid accuracy percentage claims.
- Large keyboard/screenreader accessibility and icon-based, no-reading operation remain future work. Voice prompts alone do not ensure full accessibility.
