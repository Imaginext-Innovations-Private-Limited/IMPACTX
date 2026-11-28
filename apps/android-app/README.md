# Aarogya Mesh — Native Android APK (`com.aarogyamesh.app`)

Gradle-free, reproducible Android APK packaging the offline-first **ASHA Field PWA** (`/phone/`) and **Tier-0 Watch / Family SOS Companion** (`/watch/`) into a single native Android app (**Launcher Name**: `Aarogya Mesh`).

## Architecture

- **`LocalAssetServer.java`**: Pure-Java `ServerSocket` bound strictly to `127.0.0.1` (preferred ephemeral-range port `49842` for stable origin persistence across restarts, automatic fallback to OS ephemeral port `0`). Serving over `http://127.0.0.1:<port>` provides a genuine W3C Secure Context so IndexedDB, `crypto.randomUUID()`, Service Workers, and real hardware `getUserMedia()` microphone recording work offline.
- **`MainActivity.java`**:
  - **Dual persistent `WebView` instances** (`phoneWebView` for `/phone/` and `watchWebView` for `/watch/`, toggled via `VISIBLE`/`GONE`) so switching between **ASHA Field** and **Watch / SOS** never reloads or wipes unsaved forms or audio recordings.
  - **Slim localized native top bar** supporting English (`ASHA Field`, `Watch / SOS`) and pure *Shuddh Tatsama* Hindi (`आशा क्षेत्र`, `घटिका / आपात`) synced with `aarogya.lang`.
  - **Native "Set Hub URL" dialog**: tapping the top-bar battery/network pill opens an Android `AlertDialog` to inspect, update, or clear `aarogya.hubUrl` / `aarogya.watch.hubUrl` without overwriting custom LAN subnets or cleared settings on page reloads.
  - Runtime `RECORD_AUDIO` permission handling + `WebChromeClient.onPermissionRequest` auto-grant for `127.0.0.1` origins.
  - Native `tel:` link interception (`tel:108` opens Android `Intent.ACTION_DIAL`).
  - `AarogyaNativeBridge` (`window.AarogyaNativeBridge`): battery %, RAM MB, CPU cores, online/offline network status, `vibrateEmergency()` haptic SOS pulses, `switchMode()`, `setLanguage()`, and `openHubSettings()`.
  - WebView CDP debugging enabled (`WebView.setWebContentsDebuggingEnabled(true)`).
  - Predictive back navigation via `OnBackInvokedCallback` (API 33+) with per-WebView history before minimizing cleanly.

## Prerequisites (Fedora Linux)

- JDK 21 (`javac`) — auto-discovered from `PATH`, `~/.local/share/jdk-21/bin/javac`, `JAVA_HOME`, or `/usr/lib/jvm/*/bin/javac`
- Android SDK Build Tools `34.0.0` (`aapt2`, `d8`, `zipalign`, `apksigner`) at `~/.local/share/android-sdk/build-tools/34.0.0/`
- Android Platform `android-34` at `~/.local/share/android-sdk/platforms/android-34/android.jar`
- Debug keystore at `~/.android/debug.keystore` (alias `androiddebugkey`, pass `android`)

## Build

```bash
cd apps/android-app
./build_apk.sh
```

Force-rebuild the TypeScript web bundles before packaging:

```bash
REBUILD_WEB=1 ./build_apk.sh
```

Output: `apps/android-app/dist/aarogya-mesh.apk` (gitignored).

## Install & Launch on Samsung Galaxy S23 (`SM-S911U1`)

```bash
# Discover & connect Wireless ADB if unplugged
s23-adb-autoconnect --once
adb devices -l

# Install APK
adb -s "$ADB_SERIAL" install -r apps/android-app/dist/aarogya-mesh.apk

# Grant microphone permission (or allow via the in-app prompt)
adb -s "$ADB_SERIAL" shell pm grant com.aarogyamesh.app android.permission.RECORD_AUDIO

# Cold-launch
adb -s "$ADB_SERIAL" shell am start -W -S -n com.aarogyamesh.app/.MainActivity
```

## LAN PHC Hub Sync (Phone ↔ Fedora Laptop)

1. Start the Fedora PHC Hub bound to all LAN interfaces (`0.0.0.0:8000`):
   ```bash
   make run-hub
   # or directly:
   uv run uvicorn aarogya_phc_hub.app:app --host 0.0.0.0 --port 8000
   ```
2. Open **Aarogya Mesh** on the S23 (on the same Wi-Fi LAN). Tap the top-right network/hub pill (`% · WIFI ⚙`) to open **Set Hub URL** (or edit in the **Sync** tab) and enter your Fedora laptop's LAN address (e.g., `http://192.168.1.14:8000`).
3. Tap **Sync now** to exchange CRDT events and register the S23 as a live `TIER_1_PHONE` peer on the PHC Hub.
