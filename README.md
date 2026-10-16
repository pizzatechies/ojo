# OJO Sentinel for Android

**[Download ojo-sentinel.apk](https://github.com/pizzatechies/ojo/raw/android-app/ojo-sentinel.apk)** (version 1.1, Android 6 or later)

This branch only holds the app. It is kept on GitHub and is not offered on the website, which is published from the `gh-pages` branch.

The app opens to a start screen with two choices:

- **Explore the demo.** The interactive demo is built into the app and works offline. It includes the Revenue, Branches and Expiry tabs.
- **Connect to your server.** Enter your OJO Sentinel server's address and sign in. The app remembers the last four addresses.

## New in 1.1: made for live testing

- **Connect from a QR code.** The live-test server shows a QR code. Scan it with the phone camera, then tap *Open in the OJO Sentinel app*.
- **Reports download** to the phone's Downloads folder, and **Print** works (including *Save as PDF*).
- **Alerts appear as phone notifications** while the app is open.
- **A clear message** when the server can't be reached, with the usual causes.

## Installing

Open the downloaded file on the phone. Android will ask you to allow installs from your browser or file manager, because the app isn't from Google Play.

**If you have version 1.0 installed, uninstall it first.** Version 1.1 is signed with a new key, so Android will not install it over 1.0 (the message is "App not installed as package conflicts with an existing package"). Nothing is lost: the app keeps no data other than the last server addresses you typed. Updates from 1.1 onwards install over each other as normal. The original is kept here as `ojo-sentinel-1.0.apk` for anyone who needs it.

## Checking the files

| File | SHA-256 |
|---|---|
| `ojo-sentinel.apk` (1.1) | `719d7a938c8a92d581dfe8fad43de8526dcc6381ef88c457d8b5bc1b9a41bdf8` |
| `ojo-sentinel-1.0.apk` (1.0) | `b1f9f7f46bdf3014ef5f61c0da31fb5e280b3e923db9918b6d96d64215519ba2` |

The source and build script are in [`tools/android/`](https://github.com/pizzatechies/ojo/tree/gh-pages/tools/android) on the `gh-pages` branch. To publish a new version, rebuild it with `build.sh` and replace `ojo-sentinel.apk` on this branch. It must be signed with the same key as 1.1, or phones that already have the app won't accept the update.
