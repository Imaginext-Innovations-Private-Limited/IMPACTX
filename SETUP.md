# Installation and recovery

## What every laptop needs

Use a writable extracted folder, a modern Chrome, Edge or Firefox browser and **64-bit Python 3.11 or 3.12**. Open the launcher on that same computer. Government live links and initial package/model downloads require Internet. The local catalogue, rules, PDFs, saved drafts and installed AI can work offline. This distribution is source code, configuration, data and assets. Python, Ollama, model weights, Tesseract and local OS voices are installed per computer.

## Windows

1. Extract All. Open the **WelfareNavigator** folder containing **START_WINDOWS.bat**. A simple path like `C:\Projects\WelfareNavigator` is convenient.
2. Install MySQL Community Server 8.4, start the local MySQL service and run SETUP_MYSQL.bat after Python installation (full sequence in README_FIRST.txt). Install Python from the official Python website. Enable **Add Python to PATH**. If Windows offers the Store instead, verify `py -3.11 --version` or `py -3.12 --version` in a new terminal.
3. Double-click **START_WINDOWS.bat**. It creates a private .venv, installs core packages and attempts the local Chroma vector backend, then starts the server and browser. The installed Bootstrap-Flask distribution provides Bootstrap 5 assets locally. If Chroma installation fails, local keyword search remains available; cached embeddings can use MySQL exact-vector search.
4. Keep the window open. If port 8765 is occupied, read the actual port printed in that window. The address uses 127.0.0.1. Stop with Ctrl+C. Do not run two copies in the same data folder.
5. Open **Admin & research**, then copy the generated password from **local_data/ADMIN_FIRST_LOGIN.txt**. Use **Privacy & security** to change it. An existing database keeps its admin account. If the file is missing, run **RESET_ADMIN_WINDOWS.bat**, press Y, and open the new file. Recover a forgotten password by opening the project folder in a terminal and running `.venv\Scripts\python.exe run.py --reset-admin`.

## Mac and Linux

Use `python3 --version` to check the interpreter. Install the Python venv package if the OS distributes it separately. From an extracted writable folder run:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-core.txt
.venv/bin/python setup_mysql.py
bash START_MAC_LINUX.sh
```

For subsequent starts you can use `.venv/bin/python run.py`. Use `--no-browser` to print the local URL without opening a tab. Stop with Ctrl+C.

## Local AI and embeddings

1. Install and open Ollama from https://ollama.com/download. Use its local desktop service; on a machine without an active service run `ollama serve` in another terminal. Keep the model service bound to loopback. Select local model tags in this app.
2. Windows users can double-click **SETUP_LOCAL_AI.bat**. Equivalent commands on all platforms:

```sh
ollama pull qwen2.5:3b
ollama pull bge-m3
ollama list
```

3. Open **Admin → System settings**. Match the chat and embedding tags to the output of `ollama list`. The chat default is Qwen2.5 3B; the multilingual embedding default is BGE-M3. Confirm the exact tags, quantization, licence and sizes on the model cards before redistributing any model weights, which are downloaded independently. Official cards: https://ollama.com/library/qwen2.5:3b and https://ollama.com/library/bge-m3.
4. Open **Knowledge base → Build / refresh embeddings**. Use **Refresh** to follow the job. Repeat after importing approved passages, changing embedding models, or restoring a content backup. Existing embeddings with the same text hash and model tag are reused. Canonical vectors are cached in MySQL; Chroma indexes them locally for search.
5. Open a scheme and ask a question. **Ollama + RAG** means the local model produced a cited answer and a second local check accepted it. **Source excerpts** is a labelled fallback for an unavailable model or failed check. Open the official citation to verify the answer yourself.
6. A smaller locally installed multilingual model can be selected on a low-memory machine. Test its Telugu/Hindi comprehension on your laptop. Model calls have timeouts and bounded concurrency. In-process experiments require an active real model; an offline model produces a job error, not a research score.

## Scanned documents and voice

**Scanner.** Text PDFs can be read directly. For scanned pages and images install Tesseract 5 and the language data `eng`, `tel`, `hin`. On Windows follow the Windows installation link from https://tesseract-ocr.github.io/tessdoc/Installation.html. The usual Program Files installation is detected; otherwise set **TESSERACT_CMD** to the full path to tesseract.exe and restart. On Debian/Ubuntu install `tesseract-ocr tesseract-ocr-eng tesseract-ocr-tel tesseract-ocr-hin`. On macOS install Tesseract and its language data. Verify with `tesseract --list-langs`. A selectable-text PDF may show “embedded PDF text” instead of a confidence percentage. Scanner output needs citizen review and does not authenticate a document.

**Dictation.** Start the app once, then run **SETUP_LOCAL_VOICE.bat** on Windows. On Unix run `.venv/bin/python -m pip install -r requirements-voice.txt` and `.venv/bin/python setup_voice.py`. This downloads a multilingual faster-whisper-small model once. Subsequent transcription runs locally. **WELFARE_WHISPER_DIR** can point to an existing compatible offline model directory. Open the browser on localhost, grant microphone consent, select the correct language, record and stop. Review the transcript before using it. Typed choices always work.

**Read-aloud.** Install OS speech voices for the intended languages and restart the browser. The app selects a voice marked local by the browser; a missing Telugu/Hindi or English voice produces a visible message. Microphone and audio quality need checking on each laptop.

## Storage, backup and privacy

* **local_data/chroma/** is the persistent semantic search index. **local_data/speech-model/** holds optional voice model files. Ollama maintains its own model cache on each computer.
* For an alternative storage location set **WELFARE_DATA** to a private writable directory before starting. On PowerShell use `$env:WELFARE_DATA = "D:\Private\WelfareData"`; on Unix use `export WELFARE_DATA="$PWD/local_data"`. Only folder names you control should be used.
* Browser-specific HttpOnly session cookies control access to saved members. Retain the same browser profile and hostname; private mode or clearing cookies loses access to that session. Profiles represent consenting people in a trusted household browsing session. Use separate OS/browser profiles on shared laptops.
* The scanner processes citizen files temporarily. Keep downloads private. Give only the **original clean ZIP** to classmates. Official source originals imported by admins are kept for review. No full private identifiers are needed for the bundled worksheets. Use fictional information for demonstrations.
* Admin **System settings → Download content backup** exports policy versions, source text and files, cached embeddings and configuration. It omits citizen records, credentials and research runs. Admin **Research** exports results separately; a citizen can export or delete their own profile. Restore replaces the current policy catalogue, then rebuild the Chroma index. Use a trusted backup you created. For large policy backups run `python maintenance.py backup filename.json` or `python maintenance.py restore filename.json` from the app's venv. Each prompts for the local admin password.
* In-app reminders are checked roughly every minute while the local backend runs. They use published dates, opt-in settings and saved profiles. There is no mandatory mail/SMS provider.

## Troubleshooting

| Symptom | Action |
|---|---|
| Blank screen after extracting | Start the launcher. Open its exact local HTTP URL; opening templates/index.html directly cannot run the Python API. |
| Dependencies will not install | Retry online with 64-bit Python 3.11/3.12. If changing Python, rename the old .venv folder, then rerun the launcher. Keep local_data. |
| Chroma missing | From the project directory run `.venv\Scripts\python.exe -m pip install "chromadb>=1,<2"` on Windows or use .venv/bin/python on Unix, then re-index. |
| No AI answer / no embeddings | Check Ollama is running, model tags match, there is disk space, and the index job completed. Reduce top-k or choose a smaller installed model on a slower laptop. |
| No schemes match | Try fewer filters, check the supported state/category and review dates. The app covers its local corpus. |
| No nearby centre | Open the official directory link. The cached directory is intentionally small. |
| Voice or OCR cannot read a language | Install that language's local model/voice/data. Type the answer or manually correct the scan. |
| Need a self-check | Windows: CHECK_WINDOWS.bat. Unix: .venv/bin/python -m unittest discover -s tests -v. See docs/SOURCES_AND_TESTS.md for browser and model validation. |

The model publishers identify Qwen2.5-3B-Instruct under **Qwen Research** and BAAI BGE-M3 under **MIT**. Model licences and exact downloaded builds are independent of the application. Record the output of `ollama show qwen2.5:3b`, `ollama show bge-m3` and `ollama list` with the laptop and model configuration in your research report. Model references: https://huggingface.co/Qwen/Qwen2.5-3B-Instruct and https://huggingface.co/BAAI/bge-m3.

## Storage and backups
Personal and scheme records are in local MySQL. Back up welfare_navigator through MySQL and keep local_data/mysql.json private. The content-only admin export covers scheme knowledge.
