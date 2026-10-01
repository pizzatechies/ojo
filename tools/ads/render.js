/* Render an ad page to MP4 (H.264, 30 fps), frame by frame, plus a poster image.
 *
 *   node render.js ad1-we-see-everything-16x9.html [out.mp4] [--poster=27.9]
 *
 * Needs Playwright (Chromium) and ffmpeg. Set CHROMIUM_PATH to use a specific browser binary.
 */
const { chromium } = require("playwright");
const { spawn } = require("child_process");
const path = require("path");
const url = require("url");

(async () => {
  const [page_, outArg, ...rest] = process.argv.slice(2);
  if (!page_) { console.error("usage: node render.js <ad.html> [out.mp4] [--poster=seconds] [--fps=30]"); process.exit(2); }
  const opt = Object.fromEntries(rest.map((a) => a.replace(/^--/, "").split("=")));
  const fps = +(opt.fps || 30);
  const file = path.resolve(__dirname, page_);
  const out = path.resolve(outArg || path.join(__dirname, "out", path.basename(page_, ".html") + ".mp4"));
  require("fs").mkdirSync(path.dirname(out), { recursive: true });

  const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
  const probe = await browser.newPage();
  await probe.goto(url.pathToFileURL(file).href + "?render=1");
  const size = await probe.evaluate(() => { const r = document.getElementById("stage").getBoundingClientRect(); return { width: Math.round(r.width), height: Math.round(r.height) }; });
  await probe.close();

  const page = await browser.newPage({ viewport: size, deviceScaleFactor: 1 });
  await page.goto(url.pathToFileURL(file).href + "?render=1", { waitUntil: "load" });
  await page.evaluate(() => document.fonts.ready);
  const duration = await page.evaluate(() => window.AD.duration);
  const frames = Math.round(duration * fps);

  const ff = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(fps), "-i", "-",
    "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
    "-vf", `scale=${size.width}:${size.height}`, out], { stdio: ["pipe", "inherit", "inherit"] });
  const done = new Promise((res, rej) => ff.on("close", (c) => (c === 0 ? res() : rej(new Error("ffmpeg exited " + c)))));

  const t0 = Date.now();
  for (let i = 0; i < frames; i++) {
    await page.evaluate((t) => window.AD.frame(t), i / fps);
    const buf = await page.screenshot({ type: "jpeg", quality: 93, clip: { x: 0, y: 0, ...size } });
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once("drain", r));
    if (i % (fps * 5) === 0) process.stdout.write(`  ${path.basename(out)} ${Math.round((i / frames) * 100)}%\r`);
  }
  ff.stdin.end();
  await done;

  const posterAt = opt.poster !== undefined ? +opt.poster : duration - 1.2;
  await page.evaluate((t) => window.AD.frame(t), posterAt);
  await page.screenshot({ path: out.replace(/\.mp4$/, ".jpg"), type: "jpeg", quality: 90, clip: { x: 0, y: 0, ...size } });
  await browser.close();
  console.log(`${path.basename(out)}: ${size.width}x${size.height}, ${duration}s, ${frames} frames in ${((Date.now() - t0) / 1000).toFixed(0)}s`);
})().catch((e) => { console.error(e); process.exit(1); });
