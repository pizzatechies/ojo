/* Build the OJO Sentinel brochure for the website.
 *
 *   node build.js            # → ../../brochure/index.html and ojo-sentinel-brochure.pdf
 *
 * The 12 A4 pages in pages/ are the brochure's design files (exported from the design canvas).
 * This script lifts each page's markup into one web page, points images at the site's own copies,
 * checks that nothing runs off a page, and prints the A4 PDF. Needs Playwright (Chromium).
 * Run qr.py first if the QR codes are missing.
 */
const fs = require("fs");
const path = require("path");
const url = require("url");
const { chromium } = require("playwright");

const SITE = "https://pizzatechies.github.io/ojo/brochure/";
const OUT_DIR = path.resolve(__dirname, "../../brochure");
const PDF_NAME = "ojo-sentinel-brochure.pdf";

// Images the design canvas stored as uploads, mapped to the files the site already serves.
const BLOBS = {
  "/_blob/a10082a56f6162a63fe7132f2c9a3731": "../assets/dashboard.jpg",
  "/_blob/0e230bcfa15147d2ea559c97e7fcd968": "../assets/finance.jpg",
  "/_blob/0101cf5e9b54e5631366dbadea990d26": "../assets/autonomy.jpg",
  "/_blob/a02981f8d70f00a7c9c9fe62d9bb3478": "qr-demo.png",
};

function sheetMarkup(file) {
  const src = fs.readFileSync(file, "utf8");
  const m = src.match(/<x-dc>([\s\S]*?)<\/x-dc>/);
  if (!m) throw new Error(`${file}: no <x-dc> block`);
  let html = m[1].replace(/<helmet>[\s\S]*?<\/helmet>/, "").trim();
  html = html.replace(/\/_blob\/[0-9a-f]{32}/g, (b) => {
    if (!BLOBS[b]) throw new Error(`${file}: unknown image ${b}`);
    return BLOBS[b];
  });
  if (/\{\{/.test(html)) throw new Error(`${file}: template holes are not supported here`);
  return html;
}

const FONTS = [
  ["Archivo", 700, "archivo-latin-700-normal"], ["Archivo", 800, "archivo-latin-800-normal"], ["Archivo", 900, "archivo-latin-900-normal"],
  ["IBM Plex Sans", 400, "ibm-plex-sans-latin-400-normal"], ["IBM Plex Sans", 500, "ibm-plex-sans-latin-500-normal"],
  ["IBM Plex Sans", 600, "ibm-plex-sans-latin-600-normal"], ["IBM Plex Sans", 700, "ibm-plex-sans-latin-700-normal"],
  ["IBM Plex Mono", 500, "ibm-plex-mono-latin-500-normal"], ["IBM Plex Mono", 600, "ibm-plex-mono-latin-600-normal"],
].map(([family, weight, file]) =>
  `@font-face { font-family: "${family}"; font-weight: ${weight}; font-style: normal; font-display: swap; src: url(fonts/${file}.woff2) format("woff2"); }`).join("\n");

function page(sheets) {
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OJO Sentinel brochure</title>
<meta name="description" content="The OJO Sentinel brochure: security, stock, cash, people, tax and autonomous store operations for business owners, with plans and pricing.">
<meta property="og:title" content="OJO Sentinel brochure">
<meta property="og:description" content="We see everything they ignore. Twelve pages on what OJO Sentinel watches, how it works and what it costs.">
<meta property="og:image" content="${SITE}cover.jpg">
<meta property="og:url" content="${SITE}">
<meta name="theme-color" content="#0B0E12">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Ccircle cx='16' cy='16' r='15' fill='%23D4A017'/%3E%3Ccircle cx='16' cy='16' r='6' fill='%230B0E12'/%3E%3C/svg%3E">
<style>
${FONTS}
:root { --night: #0B0E12; --line: #25303B; --text: #E6EAEE; --muted: #9AA6B2; --gold: #D4A017; --gold-2: #F0BF3A; }
* { box-sizing: border-box; }
html { background: #161B21; }
body { margin: 0; background: #161B21; color: var(--text); font-family: "IBM Plex Sans", system-ui, sans-serif; }
a { color: var(--gold-2); }
.bar { position: sticky; top: 0; z-index: 10; background: rgba(11, 14, 18, 0.92); backdrop-filter: blur(10px); border-bottom: 1px solid var(--line); }
.bar-in { max-width: 1100px; margin: 0 auto; padding: 12px 16px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.brand { display: flex; align-items: center; gap: 10px; color: var(--text); text-decoration: none; font-family: "Archivo", sans-serif; font-weight: 800; letter-spacing: .18em; font-size: 15px; }
.eye { width: 22px; height: 22px; border-radius: 50%; background: var(--gold); display: grid; place-items: center; }
.eye::after { content: ""; width: 8px; height: 8px; border-radius: 50%; background: var(--night); }
.bar-title { color: var(--muted); font-size: 14px; }
.actions { margin-left: auto; display: flex; gap: 10px; flex-wrap: wrap; }
.btn { display: inline-flex; align-items: center; min-height: 44px; padding: 0 16px; border-radius: 10px; font-weight: 600; font-size: 15px; text-decoration: none; border: 1px solid var(--line); color: var(--text); background: #131920; }
.btn:hover { border-color: #3A4654; }
.btn-gold { background: var(--gold); border-color: var(--gold); color: var(--night); }
.btn-gold:hover { background: var(--gold-2); border-color: var(--gold-2); }
.intro { max-width: 1100px; margin: 0 auto; padding: 28px 16px 8px; display: flex; gap: 24px; align-items: center; flex-wrap: wrap; }
.intro p { margin: 0; flex: 1 1 320px; color: var(--muted); font-size: 16px; line-height: 1.55; }
.share { display: flex; gap: 14px; align-items: center; }
.share img { width: 92px; height: 92px; border-radius: 8px; background: #fff; padding: 6px; }
.share span { font-size: 13px; color: var(--muted); line-height: 1.4; max-width: 160px; }
.pages { display: flex; flex-direction: column; align-items: center; gap: 28px; padding: 24px 16px 64px; }
.sheet-wrap { width: 794px; max-width: 100%; aspect-ratio: 794 / 1123; overflow: hidden; border-radius: 4px; box-shadow: 0 20px 60px rgba(0, 0, 0, .5); background: #fff; }
.sheet { width: 794px; height: 1123px; transform-origin: top left; }
.sheet > div { margin: 0; }
footer { text-align: center; padding: 0 16px 48px; color: var(--muted); font-size: 14px; }
@page { size: A4; margin: 0; }
@media print {
  html, body { background: none; }
  .bar, .intro, footer { display: none; }
  .pages { display: block; padding: 0; }
  .sheet-wrap { width: 210mm; height: 297mm; max-width: none; aspect-ratio: auto; border-radius: 0; box-shadow: none; break-after: page; }
  .sheet-wrap:last-child { break-after: auto; }
  .sheet { transform: none !important; }
}
</style>
</head>
<body>
<header class="bar">
  <div class="bar-in">
    <a class="brand" href="../" aria-label="OJO Sentinel home"><span class="eye"></span>OJO SENTINEL</a>
    <span class="bar-title">Brochure · 12 pages</span>
    <div class="actions">
      <a class="btn btn-gold" href="${PDF_NAME}" download>Download PDF</a>
      <a class="btn" href="../demo/">Live demo</a>
    </div>
  </div>
</header>
<section class="intro" aria-label="About this brochure">
  <p>Everything OJO Sentinel watches, how it works and what it costs, in twelve A4 pages. Read it here, download the PDF to print or send, or share the QR code.</p>
  <div class="share"><img src="qr-brochure.png" width="92" height="92" alt="QR code for this brochure"><span>Scan to open this brochure on a phone. <a href="qr-brochure.png" download>Get the QR code</a></span></div>
</section>
<main class="pages">
${sheets.map((s, i) => `<section class="sheet-wrap" aria-label="Page ${i + 1} of ${sheets.length}"><div class="sheet">\n${s}\n</div></section>`).join("\n")}
</main>
<footer>OJO Sentinel · OJO Stores Management · <a href="../">pizzatechies.github.io/ojo</a></footer>
<script>
(() => {
  // Shrink each A4 page to fit narrow screens; print and wide screens use the true size.
  const fit = () => document.querySelectorAll(".sheet-wrap").forEach((w) => {
    const s = Math.min(1, w.clientWidth / 794);
    w.firstElementChild.style.transform = s < 1 ? "scale(" + s + ")" : "";
  });
  addEventListener("resize", fit);
  fit();
})();
</script>
</body>
</html>
`;
}

(async () => {
  const files = fs.readdirSync(path.join(__dirname, "pages")).filter((f) => f.endsWith(".dc.html")).sort();
  const sheets = files.map((f) => sheetMarkup(path.join(__dirname, "pages", f)));
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const index = path.join(OUT_DIR, "index.html");
  fs.writeFileSync(index, page(sheets));
  console.log(`wrote ${path.relative(process.cwd(), index)} (${sheets.length} pages)`);

  const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
  const tab = await browser.newPage({ viewport: { width: 1100, height: 1200 } });
  await tab.goto(url.pathToFileURL(index).href, { waitUntil: "load" });
  await tab.evaluate(() => document.fonts.ready);

  // Nothing may run past a page's bottom padding or out of its side margins.
  const problems = await tab.evaluate(() => {
    const out = [];
    document.querySelectorAll(".sheet > div").forEach((root, i) => {
      const r = root.getBoundingClientRect(), cs = getComputedStyle(root);
      const bottom = r.bottom - parseFloat(cs.paddingBottom) + 1;
      const flow = [...root.children].filter((c) => getComputedStyle(c).position !== "absolute");
      const last = flow[flow.length - 1];
      if (last && last.getBoundingClientRect().bottom > bottom) out.push(`page ${i + 1}: content runs ${Math.round(last.getBoundingClientRect().bottom - bottom)}px past the bottom margin`);
      root.querySelectorAll("*").forEach((el) => {
        if (el.closest("[style*='position: absolute']") && el.closest("[style*='position: absolute']").parentElement === root) return;
        const e = el.getBoundingClientRect();
        if (e.width && (e.right > r.right - 39 || e.left < r.left + 39)) out.push(`page ${i + 1}: <${el.tagName.toLowerCase()}> "${(el.textContent || "").trim().slice(0, 40)}" is within 40px of the edge`);
      });
    });
    return out;
  });
  if (problems.length) { console.error(problems.join("\n")); process.exitCode = 1; }

  await tab.emulateMedia({ media: "print" });
  const pdf = path.join(OUT_DIR, PDF_NAME);
  await tab.pdf({ path: pdf, preferCSSPageSize: true, printBackground: true });
  console.log(`wrote ${path.relative(process.cwd(), pdf)}`);

  // Cover image for link previews.
  await tab.emulateMedia({ media: "screen" });
  const cover = await tab.$(".sheet-wrap");
  await cover.screenshot({ path: path.join(OUT_DIR, "cover.jpg"), type: "jpeg", quality: 85 });

  if (process.env.SHOTS) {
    const sheets_ = await tab.$$(".sheet-wrap");
    for (let i = 0; i < sheets_.length; i++) await sheets_[i].screenshot({ path: path.join(process.env.SHOTS, `page${String(i + 1).padStart(2, "0")}.png`) });
  }
  await browser.close();
})();
