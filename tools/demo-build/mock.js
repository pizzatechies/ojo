/* OJO Sentinel demo backend: stands in for the FastAPI server inside the browser.
   Its data was captured from the real OJO Sentinel engines; the rules for who may
   see and close what mirror ojo_sentinel/alerts.py. */
(() => {
  "use strict";
  const FX = JSON.parse(document.getElementById("fixtures").textContent);
  const clone = (x) => JSON.parse(JSON.stringify(x));
  const T0 = Date.parse(FX.t0);
  const LOADED = Date.now();
  const DEMO = (window.DEMO = { now: () => T0 + (Date.now() - LOADED), iso: () => new Date(T0 + (Date.now() - LOADED)).toISOString() });

  const ADMIN = ["owner", "ojo_management"];
  const SEV_RANK = { info: 0, low: 1, medium: 2, high: 3, critical: 4 };
  const ALERTS_EP = "/api/alerts?limit=500";
  const TS_FIELDS = ["created_at", "updated_at", "occurred_at", "scanned_at", "last_seen", "last_movement_at", "last_ping_at"];
  // Endpoints whose rows are records of the same things (replace by key); everything else is a log (append).
  const KEYED = { "/api/stores": "id", "/api/assets": "id", "/api/phones": "id", "/api/shipments": "id", "/api/cameras": "id",
    "/api/employees": "id", "/api/attendance": "id", "/api/money/cashiers": "cashier" };
  const SKIP = ["/api/dashboard", "/api/modes", "/api/map", "/api/ai/learning", "/api/ai/risk"];

  let S; // demo state
  function reset() {
    const owner = clone(FX.baseline.owner);
    const mgrEmp = owner["/api/employees"].find((e) => e.code === "NBO-01-E01");
    S = {
      db: { owner, manager: clone(FX.baseline.manager) },
      alerts: owner[ALERTS_EP],
      users: {
        sirojo: { id: 1, username: "sirojo", full_name: "Sir Ojo", role: "owner", store_id: null },
        "store.nbo-01": { id: 3, username: "store.nbo-01", full_name: mgrEmp ? mgrEmp.full_name : "Store Manager", role: "manager", store_id: 1 },
      },
      nextId: 1000,
      salesExtra: {}, shortExtra: {}, missingExtra: 0,
      truckT: {},
      audit: owner["/api/audit?limit=200"],
      learning: owner["/api/ai/learning"],
    };
    S.lastHash = (S.audit[0] && S.audit[0].hash) || "0".repeat(64);
  }
  reset();
  window.DEMO_RESET = () => { reset(); emit({ topic: "demo.reset", data: {} }); };

  const userByToken = (token) => {
    const u = token && token.startsWith("demo-") ? S.users[token.slice(5)] : null;
    return u || null;
  };
  const roleOf = (u) => (ADMIN.includes(u.role) ? "owner" : "manager");

  function canView(u, a) {
    if (ADMIN.includes(u.role)) return true;
    if (!(a.audience || []).includes(u.role)) return false;
    return u.store_id == null || a.store_id == null || a.store_id === u.store_id;
  }

  // ------------------------------------------------------------------ live feed (stands in for the WebSocket)

  const sockets = new Set();
  function emit(msg) {
    for (const ws of sockets) {
      const u = ws._user;
      const d = msg.data || {};
      if (msg.topic.startsWith("alert") && !canView(u, d)) continue;
      if (msg.topic === "lockdown" && !ADMIN.includes(u.role) && u.store_id !== d.store_id) continue;
      setTimeout(() => ws.onmessage && ws.onmessage({ data: JSON.stringify(msg) }), 0);
    }
  }
  class DemoSocket {
    constructor(url) {
      const token = new URL(url, location.href).searchParams.get("token");
      this._user = userByToken(token);
      this.readyState = 0;
      setTimeout(() => {
        if (!this._user) { this.readyState = 3; this.onclose && this.onclose({}); return; }
        this.readyState = 1; sockets.add(this);
        this.onopen && this.onopen({});
        this.onmessage && this.onmessage({ data: JSON.stringify({ topic: "hello", data: { role: this._user.role } }) });
      }, 30);
    }
    send() {}
    close() { if (this.readyState === 3) return; this.readyState = 3; sockets.delete(this); this.onclose && this.onclose({}); }
  }
  window.WebSocket = DemoSocket;

  // ------------------------------------------------------------------ audit ledger (real SHA-256 chain for new entries)

  async function sha256(text) {
    try {
      const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
      return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
    } catch (_) {
      let h = 0; for (const c of text) h = (h * 31 + c.charCodeAt(0)) >>> 0;
      return h.toString(16).padStart(64, "0");
    }
  }
  async function audit(actor, action, target, data = {}) {
    const occurred_at = DEMO.iso();
    const prev_hash = S.lastHash;
    const hash = await sha256(JSON.stringify({ prev: prev_hash, actor, action, target, data, ts: occurred_at }));
    S.lastHash = hash;
    const id = (S.audit[0] ? S.audit[0].id : 0) + 1;
    S.audit.unshift({ id, actor, action, target, data, occurred_at, prev_hash, hash });
  }

  // ------------------------------------------------------------------ alerts

  function stamp(row) {
    const now = DEMO.iso();
    for (const f of TS_FIELDS) if (f in row && row[f]) row[f] = now;
    if (row.last_count && row.last_count.at) row.last_count.at = now;
    return row;
  }

  function addAlert(a) {
    const dup = S.alerts.find((x) => x.status !== "resolved" && x.rule === a.rule && x.title === a.title);
    if (dup) {
      dup.occurrences += 1; dup.updated_at = DEMO.iso();
      emit({ topic: "alert.updated", data: dup });
      return dup;
    }
    const alert = stamp({ ...clone(a), id: ++S.nextId, status: "open", feedback: null, resolved_by: null, resolution_note: "", occurrences: 1 });
    S.alerts.unshift(alert);
    const st = S.learning.find((r) => r.rule === alert.rule);
    if (st) st.fired += 1; else S.learning.push({ rule: alert.rule, fired: 1, true_positives: 0, false_positives: 0, precision: 0.5, threshold_multiplier: 1, suppressed: false });
    emit({ topic: "alert.new", data: alert });
    return alert;
  }

  function learn(rule, verdict) {
    let st = S.learning.find((r) => r.rule === rule);
    if (!st) { st = { rule, fired: 0, true_positives: 0, false_positives: 0, precision: 0.5, threshold_multiplier: 1, suppressed: false }; S.learning.push(st); }
    if (verdict === "true_positive") st.true_positives += 1; else st.false_positives += 1;
    const p = (st.true_positives + 2) / (st.true_positives + st.false_positives + 4);
    st.precision = Math.round(p * 1000) / 1000;
    st.threshold_multiplier = Math.round(Math.min(2, Math.max(0.7, 0.5 / p)) * 1000) / 1000;
    st.suppressed = st.true_positives + st.false_positives >= 20 && p < 0.1;
  }

  async function guardOverride(u, a, action) {
    if (a.owner_direct && !ADMIN.includes(u.role)) {
      await audit(u.username, "alert.override_refused", `alert:${a.id}`, { attempted: action, role: u.role });
      addAlert({
        rule: "override_attempt", pillar: "ai", severity: "high",
        title: `${u.full_name} tried to ${action} an owner-direct alert`,
        detail: `Alert #${a.id} '${a.title}' — attempt refused.`, store_id: a.store_id, subject: u.username,
        owner_direct: true, audience: ["owner", "ojo_management"], confidence: 1, mode: a.mode,
        live_feed_url: null, evidence: { alert_id: a.id, role: u.role }, created_at: 1, updated_at: 1,
      });
      throw httpError(403, "Only the business owner or OJO Stores Management may act on this alert.");
    }
  }

  // ------------------------------------------------------------------ scenarios (captured from the real engines)

  function applyPatch(role, patch) {
    const db = S.db[role];
    for (const [ep, change] of Object.entries(patch)) {
      if (ep === ALERTS_EP || SKIP.includes(ep) || ep.startsWith("/api/audit")) continue;
      if (change.replace) {
        if (ep === "/api/finance/overview" && db[ep]) {
          db[ep].compliance = clone(change.replace.compliance);
          continue;
        }
        if (ep === "/api/money/summary" && db[ep]) {
          const old = db[ep];
          const recs = [...change.replace.reconciliations.filter((r) => !old.reconciliations.some((o) => o.id === r.id)).map((r) => stamp({ ...r, id: ++S.nextId })), ...old.reconciliations];
          for (const r of recs) if (r.variance < 0 && !old.reconciliations.includes(r)) S.shortExtra[r.store_id] = (S.shortExtra[r.store_id] || 0) - r.variance;
          db[ep] = { ...change.replace, reconciliations: recs };
        } else db[ep] = clone(change.replace);
        continue;
      }
      const rows = db[ep];
      if (!Array.isArray(rows)) continue;
      const base = ep.replace(/\?.*/, "");
      const key = ep.startsWith("/api/inventory?store_id") ? (r) => `${r.store_id}:${r.sku}` : KEYED[base] ? (r) => r[KEYED[base]] : null;
      for (const row of change.upsert.slice().reverse()) {
        const r = stamp(clone(row));
        if (key) {
          const i = rows.findIndex((x) => key(x) === key(r));
          if (i >= 0) rows[i] = r; else rows.unshift(r);
        } else {
          r.id = ++S.nextId;
          rows.unshift(r);
          if (base === "/api/inventory/counts" && r.source === "sensor" && r.flagged && r.variance < 0 && role === "owner") S.missingExtra += -r.variance;
        }
      }
    }
  }

  window.DEMO_TRIGGER = async (kind) => {
    const sc = FX.scenarios[kind];
    if (!sc) return [];
    const wasLocked = new Set(S.db.owner["/api/stores"].filter((x) => x.locked_down).map((x) => x.id));
    for (const role of ["owner", "manager"]) if (sc.patch[role]) applyPatch(role, sc.patch[role]);
    const news = ((sc.patch.owner || {})[ALERTS_EP] || { upsert: [] }).upsert.filter((a) => !FX.baseline.owner[ALERTS_EP].some((b) => b.id === a.id));
    const created = [];
    // Oldest first, so the most serious follow-up (e.g. the lockdown) lands on top of the feed.
    for (const a of news.slice().sort((x, y) => x.id - y.id)) created.push(addAlert(a));
    for (const a of created) await audit("system", "alert.raised", `alert:${a.id}`, { rule: a.rule, severity: a.severity, title: a.title });
    const stores = S.db.owner["/api/stores"];
    for (const st of stores) {
      if (!st.locked_down || wasLocked.has(st.id)) continue;
      const why = created.find((a) => a.rule === "lockdown" && a.store_id === st.id);
      emit({ topic: "lockdown", data: { store_id: st.id, engaged: true, reason: why ? why.detail : `${st.name} locked down` } });
    }
    return created;
  };

  // ------------------------------------------------------------------ live activity

  const ROUTES = {};
  for (const a of FX.baseline.owner["/api/map"].assets) ROUTES[a.id] = a.route;
  function along(route, t) {
    const seg = Math.min(route.length - 2, Math.floor(t * (route.length - 1)));
    const f = t * (route.length - 1) - seg;
    const [a, b] = [route[seg], route[seg + 1]];
    return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f];
  }
  function nearestT(route, lat, lon) {
    let best = 0, bd = Infinity;
    for (let i = 0; i <= 400; i++) { const [y, x] = along(route, i / 400); const d = (y - lat) ** 2 + (x - lon) ** 2; if (d < bd) { bd = d; best = i / 400; } }
    return best;
  }
  window.DEMO_TICK = () => {
    const stores = S.db.owner["/api/stores"];
    const st = stores[Math.floor(Math.random() * stores.length)];
    const amount = Math.round(Math.exp(7.2 + Math.random() * 1.6));
    S.salesExtra[st.id] = (S.salesExtra[st.id] || 0) + amount;
    for (const role of ["owner", "manager"]) {
      const m = S.db[role]["/api/money/summary"];
      if (!m || (role === "manager" && st.id !== 1)) continue;
      m.gross_sales += amount; m.net_sales += amount;
      if (m.by_kind.sale) { m.by_kind.sale.count += 1; m.by_kind.sale.amount += amount; }
    }
    for (const a of S.db.owner["/api/assets"]) {
      const route = ROUTES[a.id];
      if (!route || a.off_route || a.last_lat == null) continue;
      if (S.truckT[a.id] == null) S.truckT[a.id] = nearestT(route, a.last_lat, a.last_lon);
      S.truckT[a.id] = Math.min(0.995, S.truckT[a.id] + 0.0015);
      [a.last_lat, a.last_lon] = along(route, S.truckT[a.id]);
      a.last_speed_kmh = Math.round(58 + Math.random() * 20);
      a.last_seen = DEMO.iso();
    }
    emit({ topic: "demo.tick", data: {} });
  };

  // ------------------------------------------------------------------ fake-email analyser (port of engines/cyber.py)

  const PROTECTED = ["ojostores.com", "ojosentinel.com"];
  const EXECS = ["sir ojo", "ojo"];
  const URGENCY = /\b(urgent(ly)?|immediately|asap|within (the )?(hour|24 ?h)|final notice|act now|suspend(ed)?|confidential|don'?t tell|keep this between us)\b/i;
  const PAYMENT = /\b(new (bank|account) (details|number)|change (of|in) (bank|account|payment)|updated? (bank|payment) (details|information)|wire transfer|remit(tance)?|gift cards?|m-?pesa (till|paybill) (has )?changed|pay(ment)? to (this|the following) account)\b/i;
  const LURE = /\b(verify your (account|password|identity)|reset your password|login to (confirm|continue)|your (mailbox|account) (is|will be) (full|disabled|locked))\b/i;
  const RISKY_TLDS = new Set(["zip", "mov", "xyz", "top", "click", "country", "kim", "gq", "tk", "ml", "cf", "work", "rest"]);
  const CONF = { "0": "o", "1": "l", "3": "e", "5": "s", "@": "a", "$": "s", "|": "l", "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x" };
  const skeleton = (d) => [...d.toLowerCase()].map((c) => CONF[c] || c).join("").replace(/rn/g, "m").replace(/vv/g, "w");
  function lev(a, b) {
    let prev = [...Array(b.length + 1).keys()];
    for (let i = 1; i <= a.length; i++) {
      const cur = [i];
      for (let j = 1; j <= b.length; j++) cur.push(Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] !== b[j - 1] ? 1 : 0)));
      prev = cur;
    }
    return prev[b.length];
  }
  function lookalike(domain) {
    const d = domain.toLowerCase().replace(/\.$/, "");
    if (PROTECTED.some((p) => d === p || d.endsWith("." + p))) return null;
    for (const p of PROTECTED) {
      const dn = d.split(".")[0], pn = p.split(".")[0];
      if (skeleton(d) === skeleton(p) || skeleton(dn) === skeleton(pn)) return p;
      if (pn.length >= 5 && lev(dn, pn) <= 2) return p;
      if (dn.includes(pn) && dn !== pn) return p;
    }
    return null;
  }
  const parseAddr = (s) => { const m = /^\s*"?([^"<]*?)"?\s*<([^>]+)>\s*$/.exec(s || ""); return m ? [m[1].trim(), m[2].trim()] : ["", (s || "").trim()]; };
  const domainOf = (s) => (parseAddr(s)[1].split("@")[1] || "").toLowerCase();
  const hostOf = (u) => { try { return new URL(u.includes("://") ? u : "http://" + u).hostname.toLowerCase(); } catch (_) { return ""; } };
  function analyseEmail(b) {
    const [display, addr] = parseAddr(b.sender);
    const dom = domainOf(b.sender);
    const text = `${b.subject || ""}\n${b.body || ""}`;
    const R = [];
    const auth = (b.authentication_results || "").toLowerCase();
    for (const mech of ["spf", "dkim", "dmarc"]) {
      const m = new RegExp(mech + "=(\\w+)").exec(auth);
      if (m && ["fail", "softfail", "permerror"].includes(m[1])) R.push([mech === "dmarc" ? 0.25 : 0.15, `${mech.toUpperCase()} ${m[1]}`]);
    }
    const look = dom ? lookalike(dom) : null;
    if (look) R.push([0.45, `Sender domain '${dom}' imitates '${look}'`]);
    const internal = PROTECTED.some((p) => dom === p || dom.endsWith("." + p));
    if (display && EXECS.some((e) => display.toLowerCase().includes(e)) && !internal) R.push([0.4, `Display name '${display}' impersonates an executive from external domain ${dom}`]);
    if (b.reply_to && domainOf(b.reply_to) && domainOf(b.reply_to) !== dom) R.push([0.2, `Reply-To goes to a different domain (${domainOf(b.reply_to)})`]);
    if (URGENCY.test(text)) R.push([0.1, "Pressure / urgency language"]);
    if (PAYMENT.test(text)) R.push([0.3, "Requests payment or bank-detail change"]);
    if (LURE.test(text)) R.push([0.25, "Credential-harvesting lure"]);
    for (const l of b.links || []) {
      const host = hostOf(l.href || "");
      if (!host) continue;
      if (/^[\d.]+$/.test(host)) R.push([0.25, `Link points to a raw IP address (${host})`]);
      if (RISKY_TLDS.has(host.split(".").pop())) R.push([0.15, `Link uses high-risk TLD (${host})`]);
      const shown = hostOf(l.text || "");
      if (shown.includes(".") && shown !== host) R.push([0.3, `Link text shows ${shown} but goes to ${host}`]);
      const ll = lookalike(host);
      if (ll) R.push([0.35, `Link host '${host}' imitates '${ll}'`]);
    }
    const score = Math.min(1, R.reduce((a, [w]) => a + w, 0));
    const verdict = score >= 0.6 ? "malicious" : score >= 0.3 ? "suspicious" : "clean";
    return { addr, dom, score: Math.round(score * 1000) / 1000, verdict, reasons: R.map(([, r]) => r) };
  }

  // ------------------------------------------------------------------ router

  function httpError(status, detail) { const e = new Error(detail); e.status = status; return e; }
  function dashboard(u) {
    const role = roleOf(u);
    const d = clone(S.db[role]["/api/dashboard"]);
    const visible = S.alerts.filter((a) => canView(u, a));
    const open = visible.filter((a) => a.status !== "resolved");
    const stores = S.db.owner["/api/stores"];
    d.generated_at = DEMO.iso();
    d.totals.alerts_by_severity = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
    for (const a of open) d.totals.alerts_by_severity[a.severity] += 1;
    d.totals.open_alerts = open.length;
    for (const s of d.stores) {
      const so = open.filter((a) => a.store_id === s.id);
      s.open_alerts = so.length;
      s.worst_alert = so.length ? so.reduce((w, a) => (SEV_RANK[a.severity] > SEV_RANK[w.severity] ? a : w)).severity : null;
      s.locked_down = !!(stores.find((x) => x.id === s.id) || {}).locked_down;
      s.sales_24h += S.salesExtra[s.id] || 0;
      s.cash_shortages_24h += S.shortExtra[s.id] || 0;
      const inv = S.db[role][`/api/inventory?store_id=${s.id}`];
      if (inv) s.stock_value = inv.reduce((t, r) => t + r.value, 0);
      const local = new Date(DEMO.now()).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: s.code === "LOS-01" ? "Africa/Lagos" : "Africa/Nairobi" });
      s.local_time = local;
    }
    d.totals.sales_24h = d.stores.reduce((t, s) => t + s.sales_24h, 0);
    d.totals.stock_value = d.stores.reduce((t, s) => t + s.stock_value, 0);
    d.totals.shrinkage_24h.units_missing += role === "owner" ? S.missingExtra : 0;
    d.totals.assets_off_route = (S.db.owner["/api/assets"] || []).filter((a) => a.off_route).length;
    d.recent_alerts = visible.slice(0, 25);
    return d;
  }
  function riskScores() {
    const scores = {}, counts = {};
    for (const a of S.alerts) {
      if (!a.subject || a.feedback === "false_positive") continue;
      const w = (SEV_RANK[a.severity] + 1) * (a.feedback === "true_positive" ? 2 : 1) * a.confidence;
      for (const subj of a.subject.split(", ")) { scores[subj] = (scores[subj] || 0) + w; counts[subj] = (counts[subj] || 0) + 1; }
    }
    const top = Math.max(1, ...Object.values(scores));
    return Object.entries(scores).map(([subject, v]) => ({ subject, score: Math.round(v * 100) / 100, relative: v / top, alerts: counts[subject] })).sort((a, b) => b.score - a.score);
  }
  function mapData(u) {
    const role = roleOf(u);
    const m = clone(S.db[role]["/api/map"]);
    const stores = S.db.owner["/api/stores"];
    m.stores.forEach((s) => { s.locked_down = !!(stores.find((x) => x.id === s.id) || {}).locked_down; });
    if (role === "owner") {
      m.assets = S.db.owner["/api/assets"].filter((a) => a.last_lat != null).map((a) => ({ id: a.id, code: a.code, name: a.name, kind: a.kind, lat: a.last_lat, lon: a.last_lon, speed_kmh: a.last_speed_kmh, off_route: a.off_route, route: ROUTES[a.id], last_seen: a.last_seen }));
    }
    return m;
  }

  async function handle(method, url, body, token) {
    const u0 = new URL(url, location.href);
    const path = u0.pathname;
    const q = u0.searchParams;
    if (method === "POST" && path === "/api/auth/login") {
      const u = S.users[body.username];
      const row = { id: ++S.nextId, username: body.username, ip: "197.248.10.4", success: !!u && body.password === "sentinel2026", user_agent: navigator.userAgent.slice(0, 80), occurred_at: DEMO.iso() };
      S.db.owner["/api/cyber/logins"].unshift(row);
      if (!row.success) throw httpError(401, "Invalid username or password. In this demo, sign in as sirojo or store.nbo-01 with sentinel2026.");
      await audit(u.username, "auth.login", row.ip);
      return { token: "demo-" + u.username, user: u };
    }
    const u = userByToken(token);
    if (!u) throw httpError(401, "missing credentials");
    const role = roleOf(u);
    const admin = ADMIN.includes(u.role);
    const need = (...roles) => { if (!roles.includes(u.role)) throw httpError(403, `role '${u.role}' not permitted`); };

    if (path === "/api/auth/me") return u;
    if (path === "/api/dashboard") return dashboard(u);
    if (path === "/api/map") return mapData(u);
    if (path === "/api/alerts" && method === "GET") {
      let rows = S.alerts.filter((a) => canView(u, a));
      for (const f of ["status", "severity", "pillar"]) if (q.get(f)) rows = rows.filter((a) => a[f] === q.get(f));
      return rows.slice().sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at) || b.id - a.id).slice(0, +(q.get("limit") || 100));
    }
    let m = /^\/api\/alerts\/(\d+)(?:\/(acknowledge|resolve))?$/.exec(path);
    if (m) {
      const a = S.alerts.find((x) => x.id === +m[1]);
      if (!a || !canView(u, a)) throw httpError(404, `Alert ${m[1]} not found`);
      if (!m[2]) return a;
      await guardOverride(u, a, m[2] === "acknowledge" ? "acknowledge" : "resolve");
      if (m[2] === "acknowledge") {
        if (a.status === "open") { a.status = "acknowledged"; a.updated_at = DEMO.iso(); await audit(u.username, "alert.acknowledged", `alert:${a.id}`); }
      } else {
        a.status = "resolved"; a.resolution_note = body.note || ""; a.resolved_by = u.username; a.updated_at = DEMO.iso();
        if (body.verdict) { a.feedback = body.verdict; learn(a.rule, body.verdict); }
        await audit(u.username, "alert.resolved", `alert:${a.id}`, { verdict: body.verdict, note: body.note });
      }
      emit({ topic: "alert.updated", data: a });
      return a;
    }
    m = /^\/api\/stores\/(\d+)\/lockdown(\/release)?$/.exec(path);
    if (m) {
      const id = +m[1];
      if (!admin && u.store_id !== id) throw httpError(403, "not your store");
      const store = S.db.owner["/api/stores"].find((s) => s.id === id);
      if (m[2]) {
        if (!admin) { await audit(u.username, "lockdown.release_refused", store.code, { role: u.role }); throw httpError(403, "Only the owner or OJO Stores Management can lift a lockdown."); }
        store.locked_down = false;
        for (const r of S.db.manager["/api/stores"]) if (r.id === id) r.locked_down = false;
        await audit(u.username, "lockdown.released", store.code, { reason: body.reason });
        emit({ topic: "lockdown", data: { store_id: id, engaged: false, reason: body.reason } });
        return { store: store.code, locked_down: false };
      }
      store.locked_down = true;
      for (const r of S.db.manager["/api/stores"]) if (r.id === id) r.locked_down = true;
      await audit(u.username, "lockdown.engaged", store.code, { reason: body.reason, automatic: false });
      addAlert({ rule: "lockdown", pillar: "physical", severity: "critical", title: `${store.name} LOCKED DOWN`, detail: body.reason, store_id: id,
        subject: store.code, owner_direct: true, audience: ["owner", "ojo_management", "security", "manager"], confidence: 1, mode: "day",
        live_feed_url: null, evidence: {}, created_at: 1, updated_at: 1 });
      emit({ topic: "lockdown", data: { store_id: id, engaged: true, reason: body.reason } });
      return { store: store.code, locked_down: true };
    }
    if (path === "/api/ai/learning") { need("owner", "ojo_management"); return S.learning.slice().sort((a, b) => b.fired - a.fired); }
    if (path === "/api/ai/risk") { need("owner", "ojo_management"); return riskScores(); }
    if (path === "/api/ai/scan") { need("owner", "ojo_management"); return FX.baseline.owner["/api/ai/scan"]; }
    if (path === "/api/audit") { need("owner", "ojo_management"); return S.audit.slice(0, +(q.get("limit") || 100)); }
    if (path === "/api/audit/verify") { need("owner", "ojo_management"); return { valid: true, entries_checked: S.audit.length, broken_at_id: null }; }
    if (path === "/api/cyber/email/scan" && method === "POST") {
      need("owner", "ojo_management");
      const r = analyseEmail(body);
      const scan = { id: ++S.nextId, sender: body.sender, recipient: body.recipient || "", subject: body.subject || "", score: r.score, verdict: r.verdict, reasons: r.reasons, scanned_at: DEMO.iso() };
      S.db.owner["/api/cyber/email/scans"].unshift(scan);
      if (r.verdict !== "clean") {
        addAlert({ rule: "phishing_email", pillar: "cyber", severity: r.verdict === "malicious" ? "high" : "medium",
          title: `${r.verdict === "malicious" ? "Fake" : "Suspicious"} email to ${body.recipient || "staff"}: ${(body.subject || "").slice(0, 80)}`,
          detail: r.reasons.join("; "), store_id: null, subject: r.addr || body.sender,
          owner_direct: r.reasons.some((x) => /payment|executive/i.test(x)), audience: ["owner", "ojo_management", "manager", "storekeeper", "security"],
          confidence: r.score, mode: "day", live_feed_url: null, evidence: { scan_id: scan.id, score: r.score }, created_at: 1, updated_at: 1 });
      }
      return scan;
    }
    if (path === "/api/honeypot/tokens" && method === "POST") {
      need("owner", "ojo_management");
      const rand = [...crypto.getRandomValues(new Uint8Array(12))].map((b) => "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"[b % 57]).join("");
      const prefix = { api_key: "ojo_live_", credential: "svc-", record: "SKU-" }[body.kind] || "";
      const t = { id: ++S.nextId, kind: body.kind, token: prefix + rand, label: body.label, planted_in: body.planted_in || "", active: true, created_at: DEMO.iso() };
      S.db.owner["/api/honeypot/tokens"].push(t);
      await audit(u.username, "honeypot.token_created", t.label, { kind: t.kind });
      return { ...t, canary_url: ["url", "document"].includes(t.kind) ? `${location.origin}/t/${t.token}` : undefined };
    }
    m = /^\/api\/finance\/obligations\/(\d+)\/pay$/.exec(path);
    if (m && method === "POST") { need("owner", "ojo_management"); return await payObligation(u, +m[1], body.reference || ""); }
    m = /^\/api\/finance\/licences\/(\d+)\/renew$/.exec(path);
    if (m && method === "POST") { need("owner", "ojo_management"); return await renewLicence(u, +m[1], body.new_expiry); }
    if (path === "/api/finance/sales-reports" && method === "POST") return await salesReport(u, body);
    if (method === "GET") {
      const key = path + (u0.search || "");
      const db = S.db[role];
      if (key in db) return db[key];
      if (path === "/api/inventory" && q.get("store_id")) throw httpError(403, "not your store");
      if (role === "manager") throw httpError(403, `role '${u.role}' not permitted`);
    }
    throw httpError(404, "Not available in the demo");
  }

  // ------------------------------------------------------------------ finance actions

  function rescore(ov) {
    const c = ov.compliance;
    c.score = Math.max(0, 100 - c.items.reduce((t, i) => t + i.points, 0));
    c.grade = c.score >= 85 ? "good" : c.score >= 60 ? "at risk" : "critical";
  }
  function resolveWhere(pred, note) {
    for (const a of S.alerts) {
      if (a.status !== "resolved" && pred(a)) {
        Object.assign(a, { status: "resolved", resolved_by: "system", resolution_note: note, updated_at: DEMO.iso() });
        emit({ topic: "alert.updated", data: a });
      }
    }
  }
  async function payObligation(u, id, ref) {
    const ov = S.db.owner["/api/finance/overview"];
    const L = ov.liability;
    const row = L.obligations.find((r) => r.id === id);
    if (!row) throw httpError(404, "obligation not found");
    L.obligations = L.obligations.filter((r) => r.id !== id);
    L.total_outstanding = Math.round((L.total_outstanding - row.outstanding) * 100) / 100;
    L.total_exposure = Math.round((L.total_exposure - (row.total_exposure || row.outstanding)) * 100) / 100;
    const t = L.by_tax_type.find((x) => x.tax_type === row.tax_type);
    if (t) t.outstanding = Math.max(0, Math.round((t.outstanding - row.outstanding) * 100) / 100);
    const label = row.tax_type === "instalment_tax" ? row.description : `${row.label} ${row.period}`;
    ov.compliance.items = ov.compliance.items.filter((i) => !i.text.startsWith(label));
    rescore(ov);
    const pay = S.db.owner["/api/finance/payroll"];
    if (pay && pay.period === row.period) {
      for (const r of pay.remittances) if (r.tax_type === row.tax_type) Object.assign(r, { remitted: r.deducted, variance: 0, status: row.status === "overdue" ? "paid_late" : "paid" });
    }
    if (row.tax_type === "instalment_tax") {
      const n = +String(row.reference).split("-")[1];
      const T = ov.corporate_tax;
      const sch = T.schedule.find((x) => x.instalment === n);
      if (sch) { sch.paid += row.outstanding; sch.status = row.status === "overdue" ? "paid_late" : "paid"; }
      T.instalments_paid = Math.round((T.instalments_paid + row.outstanding) * 100) / 100;
      T.shortfall = Math.max(0, Math.round((T.instalments_required_to_date - T.instalments_paid) * 100) / 100);
      if (!T.shortfall) resolveWhere((a) => a.rule === "instalment_shortfall", "Instalments up to date.");
    }
    resolveWhere((a) => a.evidence && a.evidence.obligation === id, `Paid (${ref || "no reference"}).`);
    await audit(u.username, "tax.paid", `${row.tax_type}:${row.period}:${row.reference}`, { amount: row.outstanding, ref });
    return { ...row, outstanding: 0, status: "paid" };
  }
  async function renewLicence(u, id, newExpiry) {
    const ov = S.db.owner["/api/finance/overview"];
    const lic = ov.licences.find((l) => l.id === id);
    if (!lic || !newExpiry) throw httpError(422, "Enter the new expiry date as YYYY-MM-DD.");
    const days = Math.round((Date.parse(newExpiry) - DEMO.now()) / 86400000);
    if (!(days > 0)) throw httpError(422, "the new expiry date must be in the future");
    Object.assign(lic, { expires_on: newExpiry, days_left: days, status: days <= 60 ? "renew_soon" : "valid", breach_logged_on: null });
    ov.licences.sort((a, b) => a.days_left - b.days_left);
    ov.compliance.items = ov.compliance.items.filter((i) => !i.text.startsWith(lic.name));
    rescore(ov);
    resolveWhere((a) => a.evidence && a.evidence.licence === id, `Renewed to ${newExpiry}.`);
    await audit(u.username, "licence.renewed", lic.name, { new_expiry: newExpiry });
    return lic;
  }
  async function salesReport(u, b) {
    if (!["manager", "storekeeper"].includes(u.role) && !ADMIN.includes(u.role)) throw httpError(403, "not permitted");
    const units = (S.db.owner._sales_units_nbo_7d || {})[b.sku] || 0;
    const product = (S.db.owner["/api/products"] || []).find((p) => p.sku === b.sku) || { name: b.sku, unit_price: 0 };
    const gap = units - (+b.reported_units || 0);
    const flagged = Math.abs(gap) > Math.max(2, 0.02 * Math.max(units, 1));
    if (flagged) {
      const value = Math.abs(gap) * product.unit_price;
      const vat = value * 16 / 116;
      const k = (n) => Math.round(n).toLocaleString("en-US");
      addAlert({ rule: "sales_report_mismatch", pillar: "finance", severity: "high", store_id: 1, subject: u.full_name,
        title: gap > 0 ? `${u.full_name} reported ${b.reported_units} ${product.name} sold; the system counted ${units}`
                       : `${u.full_name} reported ${-gap} more ${product.name} sold than the system recorded`,
        detail: gap > 0 ? `${gap} units (KES ${k(value)}) sold but missing from the report: the cash is unaccounted for, and if revenue is declared from these figures, VAT of KES ${k(vat)} goes undeclared.`
                        : `Sales of KES ${k(value)} claimed without till records or eTIMS invoices.`,
        owner_direct: true, audience: ["owner", "ojo_management"], confidence: 1, mode: "day", live_feed_url: null,
        evidence: { reported: +b.reported_units, system: units, gap }, created_at: 1, updated_at: 1 });
    }
    await audit(u.username, "sales.reported", `NBO-01/${b.sku}`, { reported: +b.reported_units, system: units });
    return { flagged, system_units: units, reported_units: +b.reported_units };
  }

  const realFetch = window.fetch.bind(window);
  window.fetch = async (url, opts = {}) => {
    const path = new URL(url, location.href).pathname;
    if (!path.startsWith("/api/")) return realFetch(url, opts);
    const headers = opts.headers || {};
    const token = (headers.Authorization || "").replace(/^Bearer\s+/, "");
    let body = {};
    try { body = opts.body ? JSON.parse(opts.body) : {}; } catch (_) {}
    await new Promise((r) => setTimeout(r, 60 + Math.random() * 80)); // feel like a network
    try {
      const data = await handle((opts.method || "GET").toUpperCase(), url, body, token);
      return new Response(JSON.stringify(data), { status: 200, headers: { "Content-Type": "application/json" } });
    } catch (e) {
      if (!e.status) console.error(e);
      return new Response(JSON.stringify({ detail: e.message }), { status: e.status || 500, headers: { "Content-Type": "application/json" } });
    }
  };
})();
