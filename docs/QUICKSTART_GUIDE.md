# Aarogya Mesh — Quick Start & Connection Guide

A short cheat-sheet for starting the **Laptop Hub**, launching the **Phone App**, and connecting them over **Wi-Fi, Hotspot, or USB**.

---

## 1. Start the Laptop Application (PHC Hub)

From the project root (`aarogya-mesh/`):

```bash
make run-hub
```

This builds the UI bundles (if needed) and starts the Hub on **`0.0.0.0:8000`** (listening on all local network interfaces).

Open in your laptop browser:
- **Presentation Deck**: `http://127.0.0.1:8000/deck`
- **3-Tier Live Demo Stage** (Watch + Phone + Hub): `http://127.0.0.1:8000/showcase`
- **PHC Command Center Dashboard**: `http://127.0.0.1:8000/`
- **Phone View (Browser)**: `http://127.0.0.1:8000/phone/`
- **Watch View (Browser)**: `http://127.0.0.1:8000/watch/`

---

## 2. Start the Phone App

### Option A: Native Android APK (Recommended for Phone Demo)
1. Open the **`Aarogya Mesh`** app on the phone.
2. It runs its own embedded local server (`127.0.0.1:49842`) inside the APK, so it boots and works **100% offline** even in Airplane Mode.
3. Use the top bar to switch between **ASHA Field** (`/phone/`) and **Watch / SOS** (`/watch/`), and tap the **`हिन्दी` / `EN`** toggle for language.

*(If you need to reinstall/launch via USB or Wireless ADB:)*
```bash
adb -s "$ADB_SERIAL" install -r apps/android-app/dist/aarogya-mesh.apk
adb -s "$ADB_SERIAL" shell pm grant com.aarogyamesh.app android.permission.RECORD_AUDIO
adb -s "$ADB_SERIAL" shell am start -W -S -n com.aarogyamesh.app/.MainActivity
```

### Option B: Phone Web Browser (No APK needed)
On the phone's browser (Chrome), open:
`http://<LAPTOP-IP>:8000/phone/`

---

## 3. Do They Have to Be on the Same Wi-Fi?

**Short answer:**
- **To use each app standalone (register patients, run IMNCI triage, record voice, trigger SOS):** **NO Wi-Fi or internet is needed.** Turn on Airplane Mode and both work independently.
- **To sync Phone ↔ Laptop Hub:** They just need **one local path** between them (no internet required). Pick any of the 3 options below:

### Connection Option 1: Phone Hotspot (Recommended for Restricted Wi-Fi)
*Venue Wi-Fi often blocks device-to-device traffic (AP isolation). A hotspot avoids that completely.*
1. Turn on **Mobile Hotspot** on the phone (mobile data can be **OFF**).
2. Connect your Fedora laptop to the phone's hotspot.
3. Find the laptop's IP on Fedora:
   ```bash
   hostname -I | awk '{print $1}'
   ```
4. On the phone app, tap the top-right pill (**`% · WIFI ⚙`**) → **Set Hub URL** → enter `http://<LAPTOP-IP>:8000` (e.g. `http://192.168.43.120:8000`).
5. Tap **Sync now** in the **Sync** tab.

### Connection Option 2: Same Wi-Fi Router / LAN
1. Connect both the Fedora laptop and the phone to the **same Wi-Fi**.
2. Find the laptop's IP (`hostname -I | awk '{print $1}'`).
3. Set the phone's Hub URL (**`% · WIFI ⚙`**) to `http://<LAPTOP-IP>:8000`.
4. Tap **Sync now**.

> **Fedora Firewall Note:** If the phone cannot reach port `8000` over Wi-Fi/Hotspot, open it once on Fedora:
> ```bash
> sudo firewall-cmd --add-port=8000/tcp
> ```

### Connection Option 3: USB Cable (Zero Wi-Fi Needed)
If Wi-Fi is completely unavailable or blocked:
1. Plug the phone into the laptop via USB (with USB Debugging enabled).
2. Run:
   ```bash
   adb reverse tcp:8000 tcp:8000
   ```
3. On the phone app, set Hub URL (**`% · WIFI ⚙`**) to `http://127.0.0.1:8000` and tap **Sync now**.

---

## 4. Quick Troubleshooting

| Symptom | Fix |
| --- | --- |
| Phone says Hub offline on same Wi-Fi | Venue Wi-Fi likely has **AP/Client Isolation**. Switch to **Phone Hotspot** (Option 1) or **USB `adb reverse`** (Option 3). |
| Connection refused / timeout on Fedora | Check Hub is running (`make run-hub`) and allow port `8000` in `firewalld` (`sudo firewall-cmd --add-port=8000/tcp`). |
| Unsure what IP to enter on Phone | Run `hostname -I` on the laptop and use the first IPv4 address (`http://<IP>:8000`). |

---

## 5. Tech Stack (At a Glance)

| Layer | Technology |
| --- | --- |
| **Backend / Hub (`services/phc-hub`)** | Python 3.12 (`uv`), FastAPI, Uvicorn, SQLite (WAL mode), WebSockets |
| **Phone & Watch UI (`apps/field-pwa`, `apps/watch-companion`)** | Vanilla TypeScript 5.7, `esbuild`, IndexedDB, Service Workers (zero runtime framework bloat) |
| **Android APK (`apps/android-app`)** | Native Java `WebView` + embedded `127.0.0.1` `ServerSocket` (`aapt2` / `d8` / `apksigner`, Gradle-free) |
| **Sync & Contracts (`packages/*`)** | Custom HLC + CRDT append-only event log, Pydantic v2 + JSON Schema (`contracts`) |
| **Clinical & Edge ML (`packages/clinical-engine`, `services/ml-pipeline`)** | Deterministic WHO IMNCI + India UIP rules; optional CPU INT8 `faster-whisper`, `llama-cpp-python`, `lightgbm`, EWMA |
