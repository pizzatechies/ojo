#!/usr/bin/env bash
# Build the OJO Sentinel Android app (a WebView shell around the demo and the owner's own server).
#
# Needs: a JDK, Python 3 with Pillow, and the Android build tools. On Ubuntu/Debian:
#   apt-get install android-sdk-platform-23 aapt dalvik-exchange zipalign apksigner
#
# Signing: set KEYSTORE (and KEYSTORE_PASS, KEY_ALIAS) to your release key. Keep that key safe:
# every update must be signed with the same key. Without it a throwaway key is generated.
set -euo pipefail
cd "$(dirname "$0")"

ANDROID_JAR=${ANDROID_JAR:-/usr/lib/android-sdk/platforms/android-23/android.jar}
DX=${DX:-/usr/lib/android-sdk/build-tools/debian/dx}
DEMO_HTML=${DEMO_HTML:-../../demo/index.html}
OUT=${OUT:-build/ojo-sentinel.apk}
PKG_DIR=com/ojostores/sentinel

rm -rf build && mkdir -p build/gen build/classes build/res build/assets/demo
python3 icons.py build/res
cp -r assets/. build/assets/
# The website's standalone demo, with its "About" link pointed back at the app's start screen.
sed 's#<a href="../" style="color:var(--gold)">← About OJO Sentinel</a>#<a href="../index.html" style="color:var(--gold)">← Back to start</a>#' \
  "$DEMO_HTML" > build/assets/demo/index.html
grep -q 'Back to start' build/assets/demo/index.html || { echo "demo link not rewritten" >&2; exit 1; }
cp ../../favicon.svg build/assets/favicon.svg

aapt package -f -m -J build/gen -M AndroidManifest.xml -S res -S build/res --auto-add-overlay -I "$ANDROID_JAR"
javac -nowarn -Xlint:-options -source 8 -target 8 -bootclasspath "$ANDROID_JAR" -d build/classes \
  build/gen/$PKG_DIR/R.java src/$PKG_DIR/*.java
"$DX" --dex --output=build/classes.dex build/classes
aapt package -f -M AndroidManifest.xml -S res -S build/res --auto-add-overlay -A build/assets -I "$ANDROID_JAR" \
  -F build/unsigned.apk
(cd build && aapt add -f unsigned.apk classes.dex >/dev/null)
zipalign -f -p 4 build/unsigned.apk build/aligned.apk

if [ -z "${KEYSTORE:-}" ]; then
  KEYSTORE=build/throwaway.jks KEYSTORE_PASS=android KEY_ALIAS=ojo
  keytool -genkeypair -keystore "$KEYSTORE" -storepass "$KEYSTORE_PASS" -keypass "$KEYSTORE_PASS" -alias "$KEY_ALIAS" \
    -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=OJO Sentinel, O=OJO Stores Management, C=KE" >/dev/null 2>&1
fi
mkdir -p "$(dirname "$OUT")"
apksigner sign --v4-signing-enabled false --ks "$KEYSTORE" --ks-pass "pass:${KEYSTORE_PASS}" --ks-key-alias "${KEY_ALIAS}" --out "$OUT" build/aligned.apk
apksigner verify "$OUT"
echo "Built $OUT ($(du -h "$OUT" | cut -f1))"
