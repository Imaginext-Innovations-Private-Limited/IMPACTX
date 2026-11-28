# v1.2.1 — Create voices automatically (no recordings needed)

> Historical notes. For current v2.1 behavior and setup, see [final release guide](FINAL_RELEASE.md) and [README](../README.md).

## Quick demo setup on Windows

1. Run `run.bat` once to set up the virtual environment. This optional legacy helper covers six languages; Sarvam is the preferred seven-language path.
2. From the project folder, install the optional dependency: `.venv\Scripts\python.exe -m pip install edge-tts`. Internet is required.
3. Run `.venv\Scripts\python.exe tools\generate_voice_pack.py --risk high` (or `--risk all` for 30 clips).
4. The script uses online speech to create `static/voices/<language>/<risk>.mp3`.
5. Start/return to ScamShield using `run.bat`; press **Ctrl+F5** in the browser. Analyze a demo message, select the desired language and press **Hear warning**.
6. Voices are locally cached MP3s; once they have been generated, playback is local and does not require the network. Audio generation must be repeated for any missing files or revised text.

**Privacy:** The generator sends ONLY the application's five predefined, fixed warning messages per language. It does not send users' SMS content, OTPs, screenshots, evidence, complaints, or calls. Do not modify it to send personal content to a third-party TTS service.

**Provider limitation:** This demo helper uses the community-maintained `edge-tts` client for an online service associated with Microsoft Edge. It is not an officially supported Azure TTS API, and it may fail or change without notice. Review terms and permissions before any commercial/public deployment or redistribution of audio files. For a production product, integrate an officially supported provider (e.g. Azure Speech) using server-side credentials and an account-approved pricing tier. Azure Speech documentation lists voices for all six language options. 

**Verification:** The MP3 files cannot be synthesized or playback-tested in the build environment here. On your laptop verify that all selected generated files are valid and audible; your teammates should listen for correct local wording and pronunciation, especially Odia and numbers like 1930. Never claim the audio works until it does on the demonstration laptop.

## Troubleshooting

- If you see `pip` or connection errors, check internet and rerun the Python generator above.
- If a voice fails, the script shows **FAIL** and exits with an incomplete status. Existing good MP3 files are not downloaded again.
- If the app still says no voice, ensure the file exists, for example `static/voices/hi/high.mp3`, then press Ctrl+F5.
- If you used native recordings, those `.webm` files are still supported and have precedence over the generated `.mp3` files.
- If no voice can be downloaded, the browser's own speech synthesis voice or written warning remains the fallback.
