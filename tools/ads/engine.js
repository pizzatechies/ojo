/* OJO Sentinel ad engine: a deterministic timeline, so every frame can be rendered exactly.
 *
 * Any element with data-at="start end" (seconds) is shown between those times, entering and leaving
 * with the effect named in data-fx (fade, up, down, left, right, scale, pop, blur, wipe, type, count).
 * data-in / data-out set the entrance and exit durations. window.AD.frame(t) draws time t, and
 * window.AD.duration is the length. Ads can register extra per-frame work with AD.on((t) => …).
 * Opened normally in a browser, the ad plays in real time and loops.
 */
(() => {
  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
  const ease = (x) => 1 - Math.pow(1 - clamp(x), 3);                 // ease-out cubic
  const easeIO = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
  const hooks = [];
  const items = [...document.querySelectorAll("[data-at]")].map((el) => {
    const [a, b] = el.dataset.at.split(/\s+/).map(Number);
    const fx = (el.dataset.fx || "fade").split(/\s+/);
    if (fx.includes("type")) el.dataset.text = el.textContent;
    if (fx.includes("count")) el.dataset.text = el.textContent;
    return { el, a, b: Number.isFinite(b) ? b : Infinity, fx, din: +(el.dataset.in || 0.6), dout: +(el.dataset.out || 0.4),
             dist: +(el.dataset.dist || 60) };
  });

  function fmtCount(el, p) {
    const to = +el.dataset.to, from = +(el.dataset.from || 0);
    const v = from + (to - from) * easeIO(clamp(p));
    const dec = +(el.dataset.dec || 0);
    const s = v.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec });
    return (el.dataset.prefix || "") + s + (el.dataset.suffix || "");
  }

  function frame(t) {
    for (const it of items) {
      const { el, a, b, fx, din, dout, dist } = it;
      if (t < a || t >= b) { el.style.visibility = "hidden"; continue; }
      el.style.visibility = "visible";
      const pin = ease((t - a) / din);
      const pout = b === Infinity ? 0 : ease((t - (b - dout)) / dout);
      const shown = pin * (1 - pout);
      let tx = 0, ty = 0, sc = 1, blur = 0, clip = null;
      if (fx.includes("up")) ty = (1 - pin) * dist - pout * dist * 0.4;
      if (fx.includes("down")) ty = -(1 - pin) * dist;
      if (fx.includes("left")) tx = (1 - pin) * dist;
      if (fx.includes("right")) tx = -(1 - pin) * dist;
      if (fx.includes("scale")) sc = 0.92 + 0.08 * pin;
      if (fx.includes("pop")) { const x = clamp((t - a) / din); sc = x < 1 ? 0.6 + 0.4 * (1 - Math.pow(1 - x, 3)) + Math.sin(x * Math.PI) * 0.08 : 1; }
      if (fx.includes("blur")) blur = (1 - pin) * 14;
      if (fx.includes("wipe")) clip = `inset(0 ${100 - pin * 100}% 0 0)`;
      if (fx.includes("zoom")) { const k = clamp((t - a) / (b - a)); sc = 1 + 0.08 * k; }
      el.style.opacity = fx.includes("none") ? 1 : shown;
      el.style.transform = `translate(${tx}px, ${ty}px) scale(${sc})`;
      el.style.filter = blur ? `blur(${blur}px)` : "";
      if (clip) el.style.clipPath = clip;
      if (fx.includes("type")) {
        const full = el.dataset.text, cps = +(el.dataset.cps || 28);
        el.textContent = full.slice(0, Math.floor((t - a) * cps));
      }
      if (fx.includes("count")) el.textContent = fmtCount(el, (t - a) / +(el.dataset.cd || 1.2));
    }
    for (const h of hooks) h(t, { clamp, ease, easeIO });
  }

  const duration = +(document.body.dataset.duration || 15);
  window.AD = { frame, duration, on: (fn) => hooks.push(fn), clamp, ease, easeIO };

  // Live preview when opened in a browser (the renderer sets ?render=1 and drives frames itself).
  if (!/[?&]render=1/.test(location.search)) {
    const start = performance.now();
    const tick = () => { frame(((performance.now() - start) / 1000) % duration); requestAnimationFrame(tick); };
    document.fonts.ready.then(() => requestAnimationFrame(tick));
  } else frame(0);
})();
