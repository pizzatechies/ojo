# OJO Sentinel — website & live demo

**We See Everything They Ignore.**

This repository hosts the public website for **OJO Sentinel**, the AI-powered business-intelligence and security platform from OJO Stores Management, plus an interactive demo of the owner's command centre.

| Path | What it is |
|---|---|
| `index.html` | The advertising site (single page, no build step) |
| `demo/` | The live demo. The real OJO Sentinel dashboard, running entirely in the browser on data captured from the real detection engines |
| `assets/` | Images used by the site |
| `tools/demo-build/` | Scripts that regenerate `demo/index.html` from the platform source |

## Hosting

The site is static and is served by **GitHub Pages** from the `gh-pages` branch:
**https://pizzatechies.github.io/ojo/** (demo at `/ojo/demo/`).

If the site isn't live, open **Settings → Pages** and set **Source** to *Deploy from a branch*, branch `gh-pages`, folder `/ (root)`.

To preview locally, run `python3 -m http.server` in this folder and open http://localhost:8000.

## The demo

The demo is the platform's own dashboard code with a small in-browser stand-in for the server (`tools/demo-build/mock.js`). It enforces the same rules as the real system:
- Managers cannot close owner-direct alerts or lift lockdowns.
- Attempts to do so are reported to the owner.
- Tamper and fraud alerts are hidden from managers.

Every alert, count and figure was produced by the real engines in the [`pizzatechies/sentinels`](https://github.com/pizzatechies/sentinels) repository. Nothing is connected to a real business.

To rebuild after changing the platform (needs a checkout of `sentinels` next to this repo, or set `SENTINELS_DIR`):

```bash
cd tools/demo-build
python3 capture.py   # runs the real engines, writes fixtures.json
python3 build.py     # writes ../../demo/index.html
```

`map.json` holds country outlines projected from Natural Earth (public domain) data.

---

*OJO Stores Management · Sir Ojo · We Are The Sentinels.*
