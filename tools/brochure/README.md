# OJO Sentinel brochure

Twelve A4 pages, published at [pizzatechies.github.io/ojo/brochure/](https://pizzatechies.github.io/ojo/brochure/) with a print-ready PDF and a QR code.

| Page | Content |
|---|---|
| 1 | Cover |
| 2 | Why it exists, and what it protects |
| 3–4 | The five pillars, feature by feature |
| 5 | The owner's dashboard, and three real alerts |
| 6 | Governance: owner-direct alerts, no manager override, the audit ledger |
| 7–8 | Tax & KRA |
| 9–10 | Autonomous Intelligence |
| 11 | Plans and pricing |
| 12 | Back cover: live demo (with QR), integrations, contact |

## Build

```sh
pip install segno && python3 qr.py      # QR codes → ../../brochure/qr-*.png, .svg
npm install playwright && node build.js # → ../../brochure/index.html, ojo-sentinel-brochure.pdf, cover.jpg
```

`pages/` holds each page's design (exported from the design canvas). `build.js` lifts them into one web page, swaps the canvas's image uploads for the site's own copies in `assets/`, fails if any page's content runs past its margins, and prints the PDF.

The back cover's contact details are placeholders (`[PHONE NUMBER]`, `[EMAIL ADDRESS]`, `[OFFICE ADDRESS]`). Fill them in `pages/Page12.dc.html` and rebuild.

Fonts: Archivo and IBM Plex, SIL Open Font License (`brochure/fonts/`).
