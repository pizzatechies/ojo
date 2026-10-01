# OJO Sentinel for Android

**[Download ojo-sentinel.apk](https://github.com/pizzatechies/ojo/raw/android-app/ojo-sentinel.apk)** (version 1.0, Android 6 or later)

This branch only holds the app. It is kept on GitHub and is not offered on the website, which is published from the `gh-pages` branch.

The app opens to a start screen with two choices:

- **Explore the demo.** The interactive demo is built into the app and works offline.
- **Connect to your server.** Enter your OJO Sentinel server's address and sign in. The app remembers the last four addresses.

## Installing

Open the downloaded file on the phone. Android will ask you to allow installs from your browser or file manager, because the app isn't from Google Play.

## Checking the file

SHA-256: `b1f9f7f46bdf3014ef5f61c0da31fb5e280b3e923db9918b6d96d64215519ba2`

The source and build script are in [`tools/android/`](https://github.com/pizzatechies/ojo/tree/gh-pages/tools/android) on the `gh-pages` branch. To publish a new version, rebuild it with `build.sh` and replace `ojo-sentinel.apk` on this branch. It must be signed with the same key, or phones that already have the app won't accept the update.
