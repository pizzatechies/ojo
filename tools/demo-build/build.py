"""Assemble the single-file OJO Sentinel demo from the real dashboard + captured fixtures."""
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).parent
SENTINELS = Path(os.environ.get("SENTINELS_DIR", HERE.parent.parent.parent / "sentinels"))
STATIC = SENTINELS / "ojo_sentinel" / "static"

# ------------------------------------------------------------------ CSS: real dashboard styles, theme tokens per page contract
css = (STATIC / "styles.css").read_text()
css = css[css.index("* { box-sizing"):]  # drop the original token blocks; replaced below
TOKENS = """
/* Layout: sticky command bar, tabbed views, floating demo panel bottom-right. Palette keeps the product's gold "eye". */
:root {
  --bg: #f3f4f6; --panel: #ffffff; --panel-2: #eceff3; --line: #d9dee5; --text: #14181d; --muted: #5a6572;
  --gold: #9a7200; --critical: #d23b43; --high: #c95f16; --medium: #a87c00; --low: #2a73c2; --info: #5a6572; --ok: #1a8a52;
  --ink-on-color: #111418; --ink-on-critical: #ffffff; --night-bg: #dfe5fb; --night-fg: #25366e; --day-bg: #fbeec3; --day-fg: #5a4400;
  --scrim: rgba(10, 12, 16, .62); --video-bg: #05070a; --video-fg: #9fb0b8; --shadow: rgba(16, 20, 26, .18);
  --land: #e2e6ec; --land-line: #c3cad4; --sea: #f7f8fa; --route: #2a73c2;
  --radius: 10px;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #0b0d10; --panel: #13171c; --panel-2: #1a2027; --line: #262e37; --text: #e7ebef; --muted: #8a96a3;
    --gold: #d4a017; --critical: #ff4d4f; --high: #ff8a3d; --medium: #f5c542; --low: #5bb3ff; --info: #8a96a3; --ok: #34c77b;
    --night-bg: #2b3a67; --night-fg: #cdd8ff; --day-bg: #5a4a12; --day-fg: #ffe9a8; --shadow: rgba(0, 0, 0, .5);
    --land: #1c232b; --land-line: #2e3843; --sea: #0f1317; --route: #5bb3ff;
    color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --bg: #0b0d10; --panel: #13171c; --panel-2: #1a2027; --line: #262e37; --text: #e7ebef; --muted: #8a96a3;
  --gold: #d4a017; --critical: #ff4d4f; --high: #ff8a3d; --medium: #f5c542; --low: #5bb3ff; --info: #8a96a3; --ok: #34c77b;
  --night-bg: #2b3a67; --night-fg: #cdd8ff; --day-bg: #5a4a12; --day-fg: #ffe9a8; --shadow: rgba(0, 0, 0, .5);
  --land: #1c232b; --land-line: #2e3843; --sea: #0f1317; --route: #5bb3ff;
  color-scheme: dark;
}
"""
css = css.replace("color: #111;", "color: var(--ink-on-color);").replace("color: #fff;", "color: var(--ink-on-critical);")
css = css.replace(".b-night { background: #2b3a67; color: #cdd8ff; }", ".b-night { background: var(--night-bg); color: var(--night-fg); }")
css = css.replace(".b-day { background: #5a4a12; color: #ffe9a8; }", ".b-day { background: var(--day-bg); color: var(--day-fg); }")
css = css.replace("background: rgba(0,0,0,.7);", "background: var(--scrim);")
css = css.replace("background: #000; color: #9aa;", "background: var(--video-bg); color: var(--video-fg);")
css = css.replace("background: #111;", "background: var(--ink-on-color);")
css = css.replace("position: sticky; top: 0;", "position: sticky; top: env(safe-area-inset-top, 0px);")
css = css.replace(".login { min-height: 100vh; display: grid; place-items: center; padding: 16px;",
                  ".login { display: grid; place-items: center; padding: 8vh 16px;")
css = css.replace("#map { height: 420px; border-radius: 8px; background: var(--panel-2); }", "")
leftover = re.findall(r"#[0-9a-fA-F]{3,6}\b|rgba?\(", css)
assert not leftover, leftover

EXTRA_CSS = """
html, body { background: var(--bg); color: var(--text); }
:focus-visible { outline: 2px solid var(--gold); outline-offset: 2px; }
/* intro */
.intro { width: min(600px, 100%); display: grid; gap: 18px; background: var(--panel); border: 1px solid var(--line); padding: 28px; border-radius: 14px; }
.intro h1 { margin: 0; font-size: clamp(22px, 4vw, 30px); line-height: 1.2; text-wrap: balance; }
.intro p { margin: 0; color: var(--muted); max-width: 62ch; }
.intro .choices { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; }
.choice { display: grid; gap: 2px; text-align: left; padding: 12px 14px; }
.choice small { font-weight: 500; opacity: .8; }
.choice.ghost small { color: var(--muted); opacity: 1; }
.intro details { color: var(--muted); font-size: 13px; }
.intro details form { display: grid; gap: 8px; margin-top: 10px; }
.demo-tag { font-size: 11px; letter-spacing: .08em; text-transform: uppercase; color: var(--gold); font-weight: 700; }
/* map */
#map { border-radius: 8px; background: var(--sea); overflow: hidden; }
#map svg { display: block; width: 100%; height: auto; }
#map .land { fill: var(--land); stroke: var(--land-line); stroke-width: .8; }
#map .country { fill: var(--muted); font-size: 11px; letter-spacing: .12em; text-transform: uppercase; opacity: .7; }
#map .route { fill: none; stroke: var(--route); stroke-width: 1.6; stroke-dasharray: 4 5; opacity: .55; }
#map .store { fill: var(--gold); stroke: var(--panel); stroke-width: 2; }
#map .store-ring { fill: none; stroke: var(--gold); stroke-width: 1.2; opacity: .5; }
#map .store.locked, #map .store-ring.locked { fill: var(--critical); stroke: var(--critical); }
#map .store-ring.locked { fill: none; animation: pulse 1.4s infinite; }
#map .store-label { fill: var(--text); font-size: 12px; font-weight: 700; }
#map .store-sub { fill: var(--muted); font-size: 10.5px; }
#map .asset { fill: var(--route); stroke: var(--panel); stroke-width: 1.5; }
#map .asset.off { fill: var(--critical); }
#map .asset-label { fill: var(--muted); font-size: 10px; }
@keyframes pulse { 50% { opacity: .15; } }
.map-legend { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 8px; font-size: 12px; color: var(--muted); }
.map-legend i { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 5px; vertical-align: -1px; }
/* demo panel */
.demo-panel { position: fixed; right: 16px; bottom: calc(16px + env(safe-area-inset-bottom, 0px)); z-index: 2500; width: min(330px, calc(100% - 32px));
  background: var(--panel); border: 1px solid var(--gold); border-radius: 12px; box-shadow: 0 12px 32px var(--shadow); max-height: min(78vh, 640px); display: flex; flex-direction: column; }
.demo-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 10px 12px; border-bottom: 1px solid var(--line); }
.demo-panel[data-collapsed="true"] .demo-head { border-bottom: 0; }
.demo-panel[data-collapsed="true"] .demo-body { display: none; }
.demo-body { padding: 12px; display: grid; gap: 12px; overflow-y: auto; }
.demo-body h4 { margin: 0; }
.seg { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.seg button { background: transparent; color: var(--text); border: 1px solid var(--line); font-weight: 500; font-size: 13px; padding: 6px 8px; }
.seg button[aria-pressed="true"] { background: var(--gold); color: var(--ink-on-color); border-color: transparent; font-weight: 700; }
.scenarios { display: grid; gap: 6px; }
.scenario-group { margin: 10px 0 6px; }
.scenario { display: flex; justify-content: space-between; align-items: center; gap: 8px; text-align: left; background: var(--panel-2); color: var(--text); border: 1px solid var(--line); font-weight: 500; font-size: 13px; padding: 7px 10px; }
.scenario:hover { border-color: var(--gold); }
.scenario small { color: var(--muted); white-space: nowrap; font-size: 11px; }
.toggle { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.toggle input { width: auto; }
.demo-note { font-size: 12px; color: var(--muted); margin: 0; }
main { padding-bottom: 96px; }
/* On wide screens, make room for the open demo panel instead of covering content with it. */
@media (min-width: 1200px) {
  body.demo-open main { padding-right: calc(330px + 32px); }
  body.demo-open .topbar { padding-right: calc(330px + 32px); }
  .demo-panel { top: calc(76px + env(safe-area-inset-top, 0px)); max-height: calc(100vh - 100px); }
  .demo-panel[data-collapsed="true"] { top: auto; }
}
/* ask dialog */
.ask-card { width: min(460px, 100%); background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 18px; display: grid; gap: 10px; }
.ask-card label { font-weight: 600; }
@media (max-width: 640px) {
  .demo-panel { right: 12px; left: 12px; width: auto; }
  .topbar { gap: 8px; }
}
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }
"""

# ------------------------------------------------------------------ JS: the real dashboard, adapted for the demo
js = (STATIC / "app.js").read_text()

def swap(old, new, count=1):
    global js
    assert js.count(old) == count, (old, js.count(old))
    js = js.replace(old, new)

swap("const s = (Date.now() - new Date(iso).getTime()) / 1000;", "const s = (window.DEMO.now() - new Date(iso).getTime()) / 1000;")
swap("new Date(Date.now() - 86400000)", "new Date(window.DEMO.now() - 86400000)")
swap('    if ("Notification" in window && Notification.permission === "default") Notification.requestPermission().catch(() => {});\n', "")
swap('''    if ("Notification" in window && Notification.permission === "granted" && ["critical", "high"].includes(a.severity)) {
      try { new Notification(`OJO Sentinel: ${a.title}`, { body: a.detail }); } catch (_) {}
    }
''', "")
swap('      if (msg.topic === "alert.updated") scheduleRefresh();',
     '''      if (msg.topic === "alert.updated") scheduleRefresh();
      if (msg.topic === "demo.tick" && state.tab === "command") loadCommand().catch(() => {});
      if (msg.topic === "demo.reset") { updateAlertCount(0); refresh(); }''')
swap('    setInterval(() => { if (state.tab === "command") loadMap().catch(() => {}); }, 15000);',
     '    if (!state.mapTimer) state.mapTimer = setInterval(() => { if (state.tab === "command" && state.token) loadMap().catch(() => {}); }, 15000);')
swap('''    $("#app").hidden = true; $("#login").hidden = false;
  }''', '''    $("#app").hidden = true; $("#login").hidden = false;
    $("#inv-store").innerHTML = ""; $("#email-result").innerHTML = ""; $("#incident").hidden = true; updateAlertCount(0);
    document.dispatchEvent(new CustomEvent("demo:session", { detail: null }));
  }''')
swap('''    $("#who").textContent''', '''    document.dispatchEvent(new CustomEvent("demo:session", { detail: state.user }));
    $("#who").textContent''')

# A paid plan change re-applies in place: reloading would reset the demo.
swap("      setTimeout(() => location.reload(), 1800);", "      setTimeout(() => window.DEMO_LOGIN(state.user.username), 1800);")
swap("${esc(p.plan_name)} is active.</b> M-Pesa receipt ${esc(p.receipt || \"to follow\")}. Reloading…",
     "${esc(p.plan_name)} is active.</b> M-Pesa receipt ${esc(p.receipt || \"to follow\")}.")
swap('<p class="small"><span class="badge">test mode</span> M-Pesa isn\'t connected yet, so payments are simulated and no money moves.</p>',
     '<p class="small"><span class="badge">demo</span> Payments here are simulated and no money moves. Any Safaricom number works; 0700 000 001 rehearses a cancelled prompt.</p>')
swap('sub.mpesa_mode === "simulated"', 'sub.mpesa_mode === "demo"')

# In-page replacement for prompt(), which the artifact viewer blocks.
swap('''  function ask(label, value = "") {
    return Promise.resolve(window.prompt(label, value));
  }
''', '''  function ask(label, value = "") {
    return new Promise((resolve) => {
      const box = $("#ask"), input = $("#ask-input");
      $("#ask-label").textContent = label;
      input.value = value;
      box.hidden = false;
      setTimeout(() => input.focus(), 0);
      const done = (v) => { box.hidden = true; $("#ask-form").onsubmit = null; $("#ask-cancel").onclick = null; resolve(v); };
      $("#ask-form").onsubmit = (e) => { e.preventDefault(); done(input.value.trim()); };
      $("#ask-cancel").onclick = () => done(null);
    });
  }
''')

# Replace the Leaflet map (tiles can't load inside an artifact) with a drawn SVG map.
start = js.index("  async function loadMap() {")
end = js.index("  // ------------------------------------------------------------------ alerts")
js = js[:start] + r'''  const MAP_LABELS = ["Nigeria", "Cameroon", "Kenya", "Uganda", "Tanzania", "Dem. Rep. Congo", "Ethiopia", "Somalia", "Gabon", "Central African Rep."];
  async function loadMap() {
    const m = await api("/api/map");
    const G = window.DEMO_MAP;
    const P = (lat, lon) => [((lon - G.lon0) * G.k).toFixed(1), ((G.lat1 - lat) * G.k).toFixed(1)];
    const staff = {};
    m.staff.forEach((p) => { if (p.on_site) staff[p.store_id] = (staff[p.store_id] || 0) + 1; });
    const parts = [`<svg viewBox="40 90 840 330" role="img" aria-label="Map of stores, vehicles and cargo across East and West Africa">`];
    for (const c of G.countries) parts.push(`<path class="land" d="${c.d}"><title>${esc(c.name)}</title></path>`);
    for (const c of G.countries) if (MAP_LABELS.includes(c.name)) parts.push(`<text class="country" x="${c.cx}" y="${c.cy}" text-anchor="middle">${esc(c.name === "Dem. Rep. Congo" ? "DR Congo" : c.name === "Central African Rep." ? "CAR" : c.name)}</text>`);
    const drawn = new Set();
    m.assets.forEach((a) => {
      const key = JSON.stringify(a.route);
      if (a.route && !drawn.has(key)) { drawn.add(key); parts.push(`<polyline class="route" points="${a.route.map(([la, lo]) => P(la, lo).join(",")).join(" ")}"/>`); }
    });
    m.stores.forEach((s) => {
      const [x, y] = P(s.lat, s.lon);
      const lock = s.locked_down ? " locked" : "";
      const staffN = staff[s.id] || 0;
      const east = s.lon > 35;  // Nairobi and Mombasa sit near the right edge: label them on the left
      parts.push(`<g><title>${esc(s.name)}${s.locked_down ? " — LOCKED DOWN" : ""} · ${staffN} staff on site</title>
        <circle class="store-ring${lock}" cx="${x}" cy="${y}" r="13"/><circle class="store${lock}" cx="${x}" cy="${y}" r="6.5"/>
        <text class="store-label" x="${+x + (east ? -16 : 16)}" y="${+y - 2}" text-anchor="${east ? "end" : "start"}">${esc(s.code)}${s.locked_down ? " · LOCKED" : ""}</text>
        <text class="store-sub" x="${+x + (east ? -16 : 16)}" y="${+y + 11}" text-anchor="${east ? "end" : "start"}">${staffN} staff on site</text></g>`);
    });
    m.assets.forEach((a) => {
      const [x, y] = P(a.lat, a.lon);
      parts.push(`<g><title>${esc(a.name)} · ${fmt(a.speed_kmh)} km/h${a.off_route ? " · OFF ROUTE" : ""} · ${ago(a.last_seen)}</title>
        <circle class="asset${a.off_route ? " off" : ""}" cx="${x}" cy="${y}" r="${a.kind === "cargo" ? 4.5 : 5.5}"/>
        ${a.off_route ? `<text class="asset-label" x="${+x + 9}" y="${+y + 4}">${esc(a.code)} off route</text>` : ""}</g>`);
    });
    parts.push("</svg>");
    $("#map").innerHTML = parts.join("") + `<div class="map-legend"><span><i style="background:var(--gold)"></i>Store</span><span><i style="background:var(--route)"></i>Vehicle or cargo (GPS / satellite)</span><span><i style="background:var(--critical)"></i>Locked down or off route</span></div>`;
  }

''' + js[end:]

# Let the demo panel sign in and switch roles.
swap("  loadSession();\n", '''  window.DEMO_LOGIN = async (username) => {
    if (state.token) logout();
    const r = await api("/api/auth/login", { method: "POST", body: { username, password: "sentinel2026" } });
    state.token = r.token; state.user = r.user; saveSession();
    await start();
  };
  window.DEMO_TOAST = toast;

  loadSession();
''')

# ------------------------------------------------------------------ HTML body from the real index.html
html = (STATIC / "index.html").read_text()
body = html[html.index("<body>") + 6: html.index("  <script src=\"https://cdnjs")]
login_start = body.index('  <section id="login"')
login_end = body.index("</section>", login_start) + len("</section>")
body = body[:login_start] + '''  <section id="login" class="login">
    <div class="intro">
      <div class="brand big"><span class="eye"></span><div><b>OJO SENTINEL</b><small>We See Everything They Ignore</small></div></div>
      <div><div class="demo-tag">Interactive demo</div><h1>Step into the owner's command centre</h1></div>
      <p>OJO Sentinel watching four OJO Stores in Nairobi, Mombasa, Kampala and Lagos. Every figure and alert here was produced by the real OJO Sentinel detection engines. Nothing is connected to a real business.</p>
      <div class="choices">
        <button class="choice" data-login="sirojo"><span>Enter as the owner</span><small>Sir Ojo · sees every store</small></button>
        <button class="choice ghost" data-login="store.nbo-01"><span>Enter as a store manager</span><small>Nairobi CBD only</small></button>
      </div>
      <p class="small">Inside, use <b>Demo controls</b> to set off incidents, such as a weapon at the door, a storekeeper hiding a loss or a tampered delivery. Then switch roles to see what a manager can and can't do.</p>
      <details><summary>Sign in with a username instead</summary>
        <form id="login-form">
          <label for="login-user">Username</label><input id="login-user" name="username" autocomplete="username" value="sirojo" required>
          <label for="login-pass">Password</label><input id="login-pass" name="password" type="password" value="sentinel2026" required>
          <button type="submit">Sign in</button>
          <p id="login-error" class="error"></p>
        </form>
      </details>
    </div>
  </section>''' + body[login_end:]
body = body.replace('<div class="card map-card"><h3>Live map <small class="muted">stores · staff · vehicles &amp; cargo</small></h3><div id="map"></div></div>',
                    '<div class="card map-card"><h3>Live map <small class="muted">stores · staff · vehicles &amp; cargo</small></h3><div id="map" aria-live="off"></div></div>')
assert 'id="map" aria-live' in body

SCENARIOS = [
    ("weapon", "Weapon at the entrance", "Nairobi"),
    ("storekeeper_lie", "Storekeeper hides a loss", "Nairobi"),
    ("stock_theft", "Stock goes missing", "Nairobi"),
    ("tamper", "Delivery tampered in transit", "Mombasa"),
    ("restricted", "Staff enters a restricted room", "Nairobi"),
    ("watchlist", "Known shoplifter walks in", "Kampala"),
    ("off_route", "Truck leaves its route", "A109"),
    ("cash_short", "Cash missing from the till", "Lagos"),
    ("refund_spree", "Cashier refund spree", "Mombasa"),
    ("phishing", "Fake CEO payment email", "Head office"),
    ("honeypot", "Hacker takes the bait", "Systems"),
    ("phone_spoof", "Driver fakes phone location", "Fleet"),
    ("night_intrusion", "Stranger loitering at loading bay", "Lagos"),
    ("supplier_pin_inactive", "Bill from a deregistered supplier", "Tax"),
    ("sales_underreported", "Storekeeper under-reports sales", "Tax"),
    ("impersonation", "Cashier signs in as a colleague", "Nairobi"),
    ("expiry_disposal_fraud", "Good stock written off as expired", "Nairobi"),
    ("short_delivery", "Delivery signed off short", "Nairobi"),
    ("fight", "Fight on the sales floor", "Nairobi"),
    ("fall", "Customer falls and stays down", "Mombasa"),
    ("crowd_surge", "Crowd surge at the entrance", "Nairobi"),
    ("silent_witness", "Someone lingers — not yet an alert", "Nairobi"),
    ("dead_zone", "Repeated trips to a camera blind spot", "Nairobi"),
    ("asset_breach", "TV demo unit leaves its zone", "Nairobi"),
    ("cross_location", "Face from a Mombasa incident appears", "Nairobi"),
    ("power_cut", "Power cut", "Kampala"),
    ("link_down", "Internet fails over to 4G", "Nairobi"),
    ("device_hot", "Video recorder overheating", "Nairobi"),
]
GROUP_BREAKS = {k: f'</div><h4 class="scenario-group">{h}</h4><div class="scenarios">' for k, h in
                [("supplier_pin_inactive", "Tax &amp; finance"), ("impersonation", "Runs itself")]}
panel = '''
  <aside id="demo-panel" class="demo-panel" data-collapsed="false" aria-label="Demo controls" hidden>
    <div class="demo-head"><b>Demo controls</b><button id="demo-toggle" class="small ghost" aria-expanded="true">Hide</button></div>
    <div class="demo-body">
      <div><h4>Viewing as</h4>
        <div class="seg" role="group" aria-label="Viewing as">
          <button data-as="sirojo" aria-pressed="true">Owner</button>
          <button data-as="store.nbo-01" aria-pressed="false">Nairobi manager</button>
        </div>
      </div>
      <div><h4>Set off an incident</h4>
        <div class="scenarios">''' + "".join(
    (GROUP_BREAKS.get(k, "") +
     f'<button class="scenario" data-scenario="{k}"><span>{label}</span><small>{where}</small></button>') for k, label, where in SCENARIOS) + '''</div>
      </div>
      <label class="toggle" for="demo-live"><input type="checkbox" id="demo-live" checked> Live sales &amp; moving vehicles</label>
      <label class="toggle" for="demo-auto"><input type="checkbox" id="demo-auto"> A random incident every 30 seconds</label>
      <p class="demo-note">As the manager, try closing a critical alert or lifting a lockdown. It's refused and reported to the owner.</p>
      <button id="demo-reset" class="small ghost">Reset demo</button>
    </div>
  </aside>
  <div id="ask" class="incident" hidden>
    <form id="ask-form" class="ask-card">
      <label id="ask-label" for="ask-input"></label>
      <textarea id="ask-input" rows="3"></textarea>
      <div class="row"><button type="submit">Confirm</button><button type="button" id="ask-cancel" class="ghost">Cancel</button></div>
    </form>
  </div>
'''

PANEL_JS = r'''
(() => {
  const $ = (s) => document.querySelector(s);
  const panel = $("#demo-panel");
  const names = ''' + json.dumps({k: l for k, l, _ in SCENARIOS}) + r''';
  let role = null, live = null, auto = null;
  document.querySelectorAll("[data-login]").forEach((b) => b.addEventListener("click", () => window.DEMO_LOGIN(b.dataset.login)));
  document.addEventListener("demo:session", (e) => {
    role = e.detail;
    panel.hidden = !role;
    syncLayout();
    document.querySelectorAll("[data-as]").forEach((b) => b.setAttribute("aria-pressed", String(!!role && b.dataset.as === role.username)));
  });
  document.querySelectorAll("[data-as]").forEach((b) => b.addEventListener("click", () => {
    if (role && b.dataset.as !== role.username) window.DEMO_LOGIN(b.dataset.as);
  }));
  const wide = window.matchMedia("(min-width: 1200px)");
  const syncLayout = () => document.body.classList.toggle("demo-open", !panel.hidden && panel.dataset.collapsed !== "true" && wide.matches);
  if (wide.addEventListener) wide.addEventListener("change", syncLayout);
  const setCollapsed = (c) => {
    panel.dataset.collapsed = String(c);
    syncLayout();
    $("#demo-toggle").textContent = c ? "Show" : "Hide";
    $("#demo-toggle").setAttribute("aria-expanded", String(!c));
  };
  $("#demo-toggle").addEventListener("click", () => setCollapsed(panel.dataset.collapsed !== "true"));
  if (!wide.matches) setCollapsed(true);

  async function fire(kind) {
    const created = await window.DEMO_TRIGGER(kind);
    const seen = created.filter((a) => role && (["owner", "ojo_management"].includes(role.role) || ((a.audience || []).includes(role.role) && (a.store_id == null || a.store_id === role.store_id))));
    if (kind === "silent_witness") window.DEMO_TOAST("Silent Witness started recording quietly. No alert, and staff see nothing. It's on the Autonomous tab.");
    else if (!created.length) window.DEMO_TOAST(`${names[kind]}: no new alert this time.`);
    else if (!seen.length) window.DEMO_TOAST(`${names[kind]}: reported to the owner only. As the Nairobi manager you can't see it.`);
    else if (!seen.some((a) => a.severity === "critical")) window.DEMO_TOAST(`${names[kind]}: ${seen[0].title}`);
    if (!wide.matches) setCollapsed(true);
  }
  document.querySelectorAll("[data-scenario]").forEach((b) => b.addEventListener("click", () => fire(b.dataset.scenario)));

  const startLive = () => { stopLive(); live = setInterval(() => window.DEMO_TICK(), 5000); };
  const stopLive = () => { clearInterval(live); live = null; };
  $("#demo-live").addEventListener("change", (e) => (e.target.checked ? startLive() : stopLive()));
  startLive();
  $("#demo-auto").addEventListener("change", (e) => {
    clearInterval(auto);
    if (e.target.checked) {
      const kinds = Object.keys(names);
      auto = setInterval(() => fire(kinds[Math.floor(Math.random() * kinds.length)]), 30000);
    }
  });
  $("#demo-reset").addEventListener("click", () => { window.DEMO_RESET(); window.DEMO_TOAST("Demo reset to the starting state."); });
})();
'''

fixtures = json.loads((HERE / "fixtures.json").read_text())
mapdata = json.loads((HERE / "map.json").read_text())
mapdata["countries"] = [c for c in mapdata["countries"] if c["name"] not in ("France", "Yemen")]

def script_json(obj):
    return json.dumps(obj, separators=(",", ":")).replace("</", "<\\/")

page = f'''<title>OJO Sentinel Live Demo</title>
<style>
{TOKENS}
{css}
{EXTRA_CSS}
</style>
{body}
{panel}
<script type="application/json" id="fixtures">{script_json(fixtures)}</script>
<script>window.DEMO_MAP = {script_json(mapdata)};</script>
<script>
{(HERE / "mock.js").read_text()}
</script>
<script>
{js}
</script>
<script>
{PANEL_JS}
</script>
'''
(HERE / "ojo-sentinel-demo.html").write_text(page)
print(f"{len(page) / 1024:.0f} KB")

# ------------------------------------------------------------------ standalone copy for the website (/demo/)
standalone = page.replace(
    '<p class="small">Inside, use <b>Demo controls</b>',
    '<p class="small"><a href="../" style="color:var(--gold)">← About OJO Sentinel</a></p>\n      <p class="small">Inside, use <b>Demo controls</b>', 1)
assert standalone != page
(HERE.parent.parent / "demo" / "index.html").write_text(
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    '<meta name="description" content="Interactive demo of OJO Sentinel, the owner\'s command centre for stores, stock, cash, people and goods.">\n'
    '<link rel="icon" href="../favicon.svg" type="image/svg+xml">\n'
    '<style>:root{color-scheme:light}body{margin:0;font:14px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>\n'
    '</head>\n<body>\n' + standalone + '</body>\n</html>\n')
