# OJO Sentinel for Android

A small native app (`com.ojostores.sentinel`) that opens to a start screen with two choices:

* **Explore the demo.** The same interactive demo as `/demo/`, bundled in the app so it works offline.
* **Connect to your server.** Opens the owner dashboard of your own OJO Sentinel server by address. The app remembers the last four addresses, and your sign-in stays in the app.

It is a full-screen WebView. Links that aren't web pages, such as `tel:`, `mailto:` and `rtsp:` camera feeds, open in the phone's own apps. The back button goes back a page, then to the start screen.

## Build

```sh
sudo apt-get install android-sdk-platform-23 aapt dalvik-exchange zipalign apksigner python3-pil
KEYSTORE=/path/to/release.jks KEYSTORE_PASS=... KEY_ALIAS=... ./build.sh
```

This writes `build/ojo-sentinel.apk`. The website does not offer the app for download; share the file directly or publish it through an app store. Build `demo/index.html` first with `tools/demo-build/build.py`, because the app bundles it.

Keep the release key safe and out of this repository. Android only installs an update when it is signed with the same key as the installed app. If `KEYSTORE` isn't set, the script creates a throwaway key.

Requires Android 6.0 (API 23) or later. The app targets API 34. Plain `http://` server addresses are allowed for servers on a local network. Use `https://` anywhere else.
