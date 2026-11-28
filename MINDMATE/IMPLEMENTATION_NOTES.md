# MINDMATE feature integration notes

## Changes made
- `src/pages/MoodCheckinPage.tsx`: added optional browser-camera expression analysis using face-api.js, camera permission/error handling, no-face handling, a model-score indicator, and manual mood confirmation. Camera frames remain in the browser and are not uploaded or persisted. Only neutral/happy expression labels can preselect a mood; other expression classes never auto-label sadness, stress, or anxiety.
- `src/pages/CompanionPage.tsx`: added browser speech recognition input, automatic speech playback of assistant replies, listening/speaking indicators, stop controls, and graceful fallback to text chat.
- `src/pages/PomodoroPage.tsx`: replaced decrement-only timing with an absolute deadline, added pause/resume/reset, browser notification permission handling, in-page alerts, sound cues, and optional focus/short-break/long-break cycling.
- `package.json`: added `face-api.js` and `react-is`; updated esbuild to the Vite 8-compatible peer range.
- `run.bat`: corrected the Windows launcher to start the existing unified TypeScript server (`npm.cmd run dev`) instead of launching an unrelated Python/Vite split setup.
- `README.md`: documented the added features, browser requirements, privacy behaviour, and setup.

## Database compatibility
No database tables or existing API contracts were changed. Confirmed moods continue to use `/api/moods`; conversation continues to use `/api/chat`; completed focus and break sessions continue to use `/api/focus`. The existing SQLite schema is reused.

## Configuration
No new environment variables or API keys are required for these three features. The existing Gemini API key remains optional and is used only by the existing AI Companion backend. Face-expression model weights are loaded on first use from jsDelivr; therefore, first-time expression analysis requires internet access. Text mood selection remains available offline.

## Browser requirements
- Camera: browser camera permission; localhost or HTTPS.
- Voice: Web Speech API support; Chrome/Edge are recommended. Browser speech recognition may use the browser vendor's speech service; typed chat remains available.
- Notifications: permission is optional. In-app alerts and a sound cue are fallback options. If the browser/device is fully suspended or shut down, JavaScript cannot guarantee a notification at the exact timer deadline.

## Verification status
- Inspected the uploaded project structure and the existing mood, chat, focus API routes and SQLite schema.
- Validated `package.json` JSON syntax.
- Ran a TypeScript parser/type-check pass in no-resolution mode on the three modified pages. No syntax errors were reported; missing-module diagnostics are expected because dependencies were not installed in this isolated build environment.
- A full dependency install and production build could not be completed in this environment because npm package installation timed out. Please run `npm.cmd install --legacy-peer-deps` on your Windows machine, then `npm.cmd run dev`. Resolve any dependency/network issue surfaced there before the live demonstration.
- Camera model loading, real microphone recognition, notification delivery, and end-to-end browser behaviour have not been physically exercised here. They must be tested in the target browser/device.

## Important note about the uploaded database
The supplied ZIP contained `mindmate.db-wal` but did not contain the main `mindmate.db` database file. The source code and schema are preserved, but any live records that existed only in the omitted main database cannot be verified or guaranteed from this ZIP alone. The app will initialize the configured SQLite database if it does not exist.
