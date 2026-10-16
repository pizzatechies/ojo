# OJO Sentinel for Android

A small native app (`com.ojostores.sentinel`, version 1.1) that opens to a start screen with two choices:

* **Explore the demo.** The same interactive demo as `/demo/`, bundled in the app so it works offline. It includes the Revenue, Branches and Expiry tabs.
* **Connect to your server.** Opens the owner dashboard of your own OJO Sentinel server by address. The app remembers the last four addresses, and your sign-in stays in the app. A bare address on your own network (`192.168.1.20:8000`, `shop.local:8000`) is opened over `http`; anything else over `https`.

It is a full-screen WebView. Links that aren't web pages, such as `tel:`, `mailto:` and `rtsp:` camera feeds, open in the phone's own apps. The back button goes back a page, then to the start screen.

## What 1.1 adds for live testing

* **Connect from a QR code.** The live-test server prints a QR code and serves a `/connect` page. Scanning the code with the phone camera opens that page; its *Open in the OJO Sentinel app* button opens the app through `ojosentinel://connect?server=http://192.168.1.20:8000`. The start screen asks you to confirm the address before going there.
* **Downloads.** CSV and JSON reports (write-offs, compliance) are saved to the phone's Downloads folder. (Android 6 to 9 asks for storage permission the first time.)
* **Printing.** The Print button on the compliance report opens Android's print dialog, which also offers *Save as PDF*.
* **Phone notifications.** Alerts the dashboard raises while the app is open (high and critical) appear as notifications. Android 13 and later asks for permission the first time you sign in.
* **A clear message when the server can't be reached**, with the usual causes, instead of a browser error page.

Not in 1.1: notifications while the app is closed. That needs a push service (Firebase Cloud Messaging) and an account for it; until then, set `OJO_OWNER_WEBHOOK_URL` on the server to receive SMS or WhatsApp alerts instead.

## Build

```sh
sudo apt-get install android-sdk-platform-23 aapt dalvik-exchange zipalign apksigner python3-pil
COMPILE_JAR=$ANDROID_HOME/platforms/android-34/android.jar \
KEYSTORE=/path/to/release.jks KEYSTORE_PASS=... KEY_ALIAS=... ./build.sh
```

`COMPILE_JAR` is the `android.jar` of API 33 or later (from Android Studio's SDK, or `sdkmanager "platforms;android-34"`): the code uses notification and Downloads APIs that the API 23 jar from `apt` doesn't have. They are only called on phones new enough to have them.

This writes `build/ojo-sentinel.apk`. The released app is kept on GitHub, on the [`android-app` branch](https://github.com/pizzatechies/ojo/tree/android-app), and is not offered on the website. To publish a new version, replace `ojo-sentinel.apk` on that branch. Build `demo/index.html` first with `tools/demo-build/build.py`, because the app bundles it.

Keep the release key safe and out of this repository. Android only installs an update when it is signed with the same key as the installed app. If `KEYSTORE` isn't set, the script creates a throwaway key.

Requires Android 6.0 (API 23) or later. The app targets API 34. Plain `http://` server addresses are allowed for servers on a local network. Use `https://` anywhere else.
