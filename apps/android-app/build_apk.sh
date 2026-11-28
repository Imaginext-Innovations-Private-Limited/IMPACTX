#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIELD_PWA_DIR="$REPO_ROOT/apps/field-pwa"
WATCH_DIR="$REPO_ROOT/apps/watch-companion"

SDK="${ANDROID_SDK_ROOT:-$HOME/.local/share/android-sdk}"
BUILD_TOOLS="${ANDROID_BUILD_TOOLS:-$SDK/build-tools/34.0.0}"
PLATFORM_JAR="${ANDROID_PLATFORM_JAR:-$SDK/platforms/android-34/android.jar}"
KEYSTORE="${ANDROID_KEYSTORE:-$HOME/.android/debug.keystore}"
KEY_ALIAS="${ANDROID_KEY_ALIAS:-androiddebugkey}"
KEY_PASS="${ANDROID_KEY_PASS:-android}"

# Locate javac (supports Fedora installations where JDK 21 lives outside default PATH)
find_javac() {
  if [[ -n "${JAVAC_BIN:-}" && -x "${JAVAC_BIN}" ]]; then
    echo "$JAVAC_BIN"
    return
  fi
  if command -v javac >/dev/null 2>&1; then
    command -v javac
    return
  fi
  for candidate in \
    "$HOME/.local/share/jdk-21/bin/javac" \
    "${JAVA_HOME:-}/bin/javac" \
    /usr/lib/jvm/*/bin/javac; do
    if [[ -x "$candidate" ]]; then
      echo "$candidate"
      return
    fi
  done
  echo "ERROR: javac not found. Set JAVAC_BIN or install OpenJDK development tools." >&2
  exit 1
}

JAVAC="$(find_javac)"
JDK_BIN_DIR="$(dirname "$JAVAC")"
export PATH="$JDK_BIN_DIR:$PATH"

for required in "$BUILD_TOOLS/aapt2" "$BUILD_TOOLS/d8" "$BUILD_TOOLS/zipalign" "$BUILD_TOOLS/apksigner" "$PLATFORM_JAR" "$KEYSTORE"; do
  if [[ ! -e "$required" ]]; then
    echo "ERROR: Required Android toolchain file missing: $required" >&2
    exit 1
  fi
done

echo "==> [1/6] Ensuring field-pwa and watch-companion dist bundles are built..."
if [[ ! -f "$FIELD_PWA_DIR/dist/app.js" || ! -f "$FIELD_PWA_DIR/dist/app.css" || ! -f "$FIELD_PWA_DIR/dist/sw-version.js" || "${REBUILD_WEB:-0}" == "1" ]]; then
  (cd "$FIELD_PWA_DIR" && npm run build)
else
  echo "    Using existing apps/field-pwa/dist/ (set REBUILD_WEB=1 to force rebuild)"
fi

if [[ ! -f "$WATCH_DIR/dist/watch.js" || "${REBUILD_WEB:-0}" == "1" ]]; then
  (cd "$WATCH_DIR" && npm run build)
else
  echo "    Using existing apps/watch-companion/dist/ (set REBUILD_WEB=1 to force rebuild)"
fi

echo "==> [2/6] Staging runtime PWA assets into apps/android-app/assets/{phone,watch}/..."
ASSETS_DIR="$SCRIPT_DIR/assets"
BUILD_DIR="$SCRIPT_DIR/build"
DIST_DIR="$SCRIPT_DIR/dist"

rm -rf "$ASSETS_DIR" "$BUILD_DIR"
mkdir -p "$ASSETS_DIR/phone/dist" "$ASSETS_DIR/phone/icons" "$ASSETS_DIR/watch/dist" \
         "$BUILD_DIR/gen" "$BUILD_DIR/classes" "$BUILD_DIR/dex" "$DIST_DIR"

cp "$FIELD_PWA_DIR/index.html" "$FIELD_PWA_DIR/manifest.webmanifest" "$FIELD_PWA_DIR/sw.js" "$ASSETS_DIR/phone/"
cp -R "$FIELD_PWA_DIR/dist/." "$ASSETS_DIR/phone/dist/"
cp -R "$FIELD_PWA_DIR/icons/." "$ASSETS_DIR/phone/icons/"

cp "$WATCH_DIR/index.html" "$WATCH_DIR/manifest.webmanifest" "$WATCH_DIR/sw.js" "$ASSETS_DIR/watch/"
cp -R "$WATCH_DIR/dist/." "$ASSETS_DIR/watch/dist/"

echo "==> [3/6] Compiling Android resources with aapt2..."
"$BUILD_TOOLS/aapt2" compile --dir "$SCRIPT_DIR/res" -o "$BUILD_DIR/res.zip"
"$BUILD_TOOLS/aapt2" link \
  -o "$BUILD_DIR/unaligned.apk" \
  -I "$PLATFORM_JAR" \
  --manifest "$SCRIPT_DIR/AndroidManifest.xml" \
  -A "$ASSETS_DIR" \
  --java "$BUILD_DIR/gen" \
  -R "$BUILD_DIR/res.zip" \
  --auto-add-overlay

echo "==> [4/6] Compiling Java sources -> classes.dex (javac + d8)..."
mapfile -t JAVA_SOURCES < <(find "$SCRIPT_DIR/src" "$BUILD_DIR/gen" -name '*.java' | sort)
# Note: -parameters prevents JDK 21 from emitting unnamed synthetic MethodParameters entries that trigger an NPE in d8 8.2.2
"$JAVAC" \
  -parameters \
  -source 8 \
  -target 8 \
  -Xlint:-options \
  -encoding UTF-8 \
  -cp "$PLATFORM_JAR" \
  -d "$BUILD_DIR/classes" \
  "${JAVA_SOURCES[@]}"

mapfile -t CLASS_FILES < <(find "$BUILD_DIR/classes" -name '*.class' | sort)
"$BUILD_TOOLS/d8" \
  --min-api 26 \
  --lib "$PLATFORM_JAR" \
  --output "$BUILD_DIR/dex" \
  "${CLASS_FILES[@]}"

echo "==> [5/6] Packaging classes.dex, zipaligning, and signing APK..."
(cd "$BUILD_DIR/dex" && zip -q -u "$BUILD_DIR/unaligned.apk" classes.dex)
"$BUILD_TOOLS/zipalign" -f -p 4 "$BUILD_DIR/unaligned.apk" "$BUILD_DIR/aligned.apk"

OUT_APK="$DIST_DIR/aarogya-mesh.apk"
"$BUILD_TOOLS/apksigner" sign \
  --ks "$KEYSTORE" \
  --ks-key-alias "$KEY_ALIAS" \
  --ks-pass "pass:$KEY_PASS" \
  --out "$OUT_APK" \
  "$BUILD_DIR/aligned.apk"

echo "==> [6/6] Verifying signed APK..."
"$BUILD_TOOLS/apksigner" verify --verbose --print-certs "$OUT_APK"

APK_SIZE="$(stat -c '%s' "$OUT_APK")"
echo ""
echo "BUILD SUCCEEDED:"
echo "  APK:       $OUT_APK"
echo "  Size:      ${APK_SIZE} bytes ($(numfmt --to=iec-i --suffix=B "$APK_SIZE" 2>/dev/null || echo "${APK_SIZE}B"))"
echo "  Package:   com.aarogyamesh.app"
echo "  Activity:  com.aarogyamesh.app/.MainActivity"
