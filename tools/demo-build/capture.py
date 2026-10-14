"""Capture real OJO Sentinel engine output as fixtures for the browser demo."""
import json, os, random, sqlite3, sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

HERE = Path(__file__).parent
sys.path.insert(0, os.environ.get("SENTINELS_DIR", str(HERE.parent.parent.parent / "sentinels")))
import ojo_sentinel.models as models
import ojo_sentinel.modes as modes

# ---- shift the clock so the demo shows a busy mid-morning across all four stores (08:00 UTC)
_real = datetime
target = _real.now(timezone.utc).replace(hour=8, minute=0, second=0, microsecond=0)
OFFSET = target - _real.now(timezone.utc)
class FakeDT(_real):
    @classmethod
    def now(cls, tz=None):
        return _real.now(tz) + OFFSET
models.datetime = FakeDT
modes.datetime = FakeDT
import ojo_sentinel.finance.rates as frates  # noqa: E402
frates.datetime = FakeDT

import logging; logging.disable(logging.WARNING)
from fastapi.testclient import TestClient
from sqlalchemy import select
from ojo_sentinel.app import create_app
from ojo_sentinel.config import Settings
from ojo_sentinel.simulator import Simulator
from ojo_sentinel.models import Store, Product, Alert
from ojo_sentinel import alerts as alert_engine
from ojo_sentinel.engines import geo

app = create_app(Settings(database_url="sqlite://", seed_demo=True, finance_scan_minutes=0, autonomy_scan_minutes=0, intel_scan_minutes=0))
db = app.state.db
# Behave like a deployment with a voice/SMS gateway, so calls read "sent" (nothing listens on this port).
from ojo_sentinel.config import settings as _settings  # noqa: E402
_settings.call_webhook_url = "http://127.0.0.1:9/calls"
c = TestClient(app)
def tok(u):
    return {"Authorization": "Bearer " + c.post("/api/auth/login", json={"username": u, "password": "sentinel2026"}).json()["token"]}
OWNER, MGR = tok("sirojo"), tok("store.nbo-01")

sim = Simulator(db, seed=11, incident_rate=0)
sim.rng.seed(11)
for _ in range(45):
    sim.tick()

def stores():
    with db.session() as s:
        return {st.code: st for st in s.scalars(select(Store))}

CUSTOM = {}
def custom(fn):
    CUSTOM[fn.__name__] = fn
    return fn

def _ago(**kw):
    return (FakeDT.now(timezone.utc) - timedelta(**kw)).isoformat()

def _pos(st, **f):
    body = {"store_id": st.id, "kind": "sale", "cashier": "Cashier", "register_id": "R1", "method": "cash", "amount": 1000, **f}
    r = c.post("/api/transactions", headers=OWNER, json=body)
    assert r.status_code in (200, 201, 202), r.text
    return r.json()

def _cashier(st):
    with db.session() as s:
        e = s.scalars(select(models.Employee).where(models.Employee.store_id == st.id, models.Employee.job_title == "Cashier")).first()
        return e.code, e.full_name

@custom
def recall(code, st):
    r = c.post("/api/expiry/recalls", headers=OWNER, json={"batch_no": "MK-2610-A21", "issued_by": "KEBS",
               "reason": "Dairy co-op contamination notice: do not sell"}); assert r.status_code == 201, r.text

@custom
def personal_qr(code, st):
    ecode, name = _cashier(st)
    r = c.post("/api/detections", headers=OWNER, json={"store_id": st.id, "kind": "payment_device", "employee_code": ecode,
               "payload": {"register_id": "R1", "device": "personal QR code on a phone", "cashier": name}}); assert r.status_code == 200, r.text

@custom
def shadow_inventory(code, st):
    ecode, name = _cashier(st)
    r = c.post("/api/detections", headers=OWNER, json={"store_id": st.id, "kind": "staff_carrying", "employee_code": ecode,
               "zone_code": "entrance", "payload": {"description": "two cartons and a duffel bag"}}); assert r.status_code == 200, r.text
    _pos(st, cashier=name, amount=2200, items=[{"barcode": "7710000099", "quantity": 2, "price": 1100, "name": "Personal stock"}])

@custom
def ghost_sale(code, st):
    _, name = _cashier(st)
    for ago in ({"hours": 3}, {"minutes": 30}):  # this till's camera is watching and reporting customers
        c.post("/api/detections", headers=OWNER, json={"store_id": st.id, "kind": "till_customer",
               "payload": {"register_id": "R9"}, "occurred_at": _ago(**ago)})
    _pos(st, cashier=name, amount=2350.37, register_id="R9", occurred_at=_ago(minutes=20))

@custom
def receipt_fraud(code, st):
    _, name = _cashier(st)
    r = c.post("/api/revenue/receipts", headers=OWNER, json={"store_id": st.id, "receipt_no": "RCPT-88-X", "amount": 1800,
               "cashier": name, "issued_at": _ago(minutes=15)}); assert r.status_code == 201, r.text

@custom
def transfer_short(code, st):
    dest = stores()["LOS-01"]
    r = c.post("/api/transfers", headers=OWNER, json={"from_store_id": st.id, "to_store_id": dest.id,
               "items": [{"sku": "YOGH-500", "quantity": 20}], "expected_hours": 12}); assert r.status_code == 201, r.text
    ref = r.json()["reference"]
    r = c.post(f"/api/transfers/{ref}/receive", headers=OWNER, json={"received": [{"sku": "YOGH-500", "quantity": 16}],
               "condition": "damaged", "note": "four crates crushed in transit"}); assert r.status_code == 200, r.text

@custom
def branch_pattern(code, st):
    for other in ("NBO-01", "MBA-01"):
        incident(other, "cash_short")

def incident(code, kind):
    if kind in CUSTOM:  # these go through the HTTP API, like a real till or camera
        return CUSTOM[kind](code, stores()[code])
    with db.session() as s:
        st = s.scalars(select(Store).where(Store.code == code)).one()
        products = s.scalars(select(Product)).all()
        if kind == "off_route":
            from ojo_sentinel.models import TrackedAsset
            a = s.scalars(select(TrackedAsset).where(TrackedAsset.code == "TRK-KDA-101")).one()
            # A realistic detour: 25 min later, 9 km south-west of the corridor.
            geo.ingest_asset_ping(s, a, a.last_lat - 0.07, a.last_lon - 0.06, speed_kmh=38,
                                  occurred_at=models.utcnow() + timedelta(minutes=25))
            return
        if kind == "refund_spree":
            from ojo_sentinel.engines import money
            from ojo_sentinel.models import Employee
            cashier = s.scalars(select(Employee).where(Employee.store_id == st.id, Employee.job_title == "Cashier")).first().full_name
            rng = random.Random(4)
            for _ in range(30):
                money.record_transaction(s, st, kind=rng.choice(["refund", "refund", "void"]),
                                         amount=round(rng.uniform(800, 4000), 2), cashier=cashier)
            money.scan_cashiers(s, st.id)
            return
        sim.incident(s, st, products, kind)

# ---- some history so the dashboard opens mid-story
incident("MBA-01", "storekeeper_lie")
incident("KLA-01", "cash_short")
incident("LOS-01", "phishing")
with db.session() as s:
    user = s.scalars(select(models.User).where(models.User.username == "sirojo")).one()
    for a in s.scalars(select(Alert)).all():
        if a.rule == "phishing_email":
            alert_engine.resolve(s, user, a, "true_positive", "Finance confirmed it was fake; sender blocked.")
    # past verdicts so the learning table has something to show
    for _ in range(3): alert_engine.learn(s, "loitering", "false_positive")
    for _ in range(4): alert_engine.learn(s, "stock_discrepancy", "true_positive")
    for _ in range(2): alert_engine.learn(s, "late_arrival", "false_positive")
from ojo_sentinel.finance import run_scan, accounting as facc  # noqa: E402
with db.session() as s:
    run_scan(s)
# The simulator's heartbeats healed the planted device problems; put them back, then let the autonomy scan find them.
from ojo_sentinel.autonomy import run_scan as autonomy_scan, infra  # noqa: E402
from ojo_sentinel.autonomy.models import Device, ShiftReport  # noqa: E402
with db.session() as s:
    acc = s.scalars(select(Device).where(Device.code == "kla-01-acc")).one()
    acc.status, acc.last_seen = "ok", models.utcnow() - timedelta(minutes=40)
    infra.heartbeat(s, s.scalars(select(Device).where(Device.code == "mba-01-nvr")).one(), temperature_c=79.0)
    autonomy_scan(s)
with db.session() as s:
    latest = {}
    for r in s.scalars(select(ShiftReport).order_by(ShiftReport.generated_at)):
        latest[r.store_id] = r.id
REPORT_EP = [f"/api/autonomy/shift-reports/{i}" for i in latest.values()]

# ---- the three intelligence modules: some history so their tabs open mid-story
from ojo_sentinel import revenue as rev_mod, branches as br_mod, expiryintel as exp_mod  # noqa: E402

def intel_scan(mods=(rev_mod, br_mod, exp_mod)):
    """What the one-minute background scanner does on a live server."""
    with db.session() as s:
        for mod in mods:
            # Payments and sales are judged once they are older than the matching grace (5 minutes): look a few minutes on.
            mod.run_scan(s, FakeDT.now(timezone.utc) + timedelta(minutes=6)) if mod is rev_mod else mod.run_scan(s)

incident("MBA-01", "unregistered_sale")   # a held sale waiting on the owner
incident("KLA-01", "mpesa_orphan")         # money received with no sale behind it
with db.session() as s:
    _stores = {st.code: st.id for st in s.scalars(select(Store))}
r = c.post("/api/transfers", headers=OWNER, json={"from_store_id": _stores["NBO-01"], "to_store_id": _stores["MBA-01"],
                                                   "items": [{"sku": "MILK-500", "quantity": 15}], "expected_hours": 6})
assert r.status_code == 201, r.text
for code, temp in (("NBO-01", 4.6), ("MBA-01", 5.2), ("KLA-01", 3.9), ("LOS-01", 6.1)):  # every chiller reporting, in range
    r = c.post("/api/expiry/temperature", headers=OWNER, json={"store_id": _stores[code], "zone": "chiller", "temp_c": temp, "sensor": "chiller-probe-1"})
    assert r.status_code == 201, r.text
r = c.post("/api/expiry/dispose", headers=OWNER, json={"store_id": _stores["NBO-01"], "sku": "FLOUR-2", "quantity": 10,
           "note": "expired: pulled from the shelf"}); assert r.status_code == 201, r.text  # a write-off on the books
for code in ("NBO-01", "MBA-01"):  # end-of-day summaries already written for two branches
    r = c.post(f"/api/branches/{_stores[code]}/summary", headers=OWNER); assert r.status_code == 201, r.text
intel_scan()
# templates for the summaries the owner can ask for from the dashboard; written, copied, then taken back out
_raw = db.engine.raw_connection()
_pre = sqlite3.connect(":memory:")
_raw.driver_connection.backup(_pre)
SUMMARY_TEMPLATES = {}
for code in ("LOS-01", "KLA-01"):
    r = c.post(f"/api/branches/{_stores[code]}/summary", headers=OWNER); assert r.status_code == 201, r.text
    SUMMARY_TEMPLATES[_stores[code]] = r.json()
_pre.backup(_raw.driver_connection)
TODAY = frates.kenya_today()

OWNER_EP = ["/api/dashboard", "/api/stores", "/api/alerts?limit=500", "/api/inventory/counts?flagged=true&limit=30",
            "/api/shipments", "/api/attendance", "/api/employees", "/api/assets", "/api/phones", "/api/modes",
            "/api/cameras", "/api/detections?limit=40", "/api/honeypot/tokens", "/api/honeypot/hits",
            "/api/cyber/email/scans", "/api/cyber/logins", "/api/money/summary", "/api/money/cashiers",
            "/api/money/benford", "/api/ai/risk", "/api/ai/learning", "/api/audit?limit=200", "/api/map",
            "/api/products", "/api/finance/overview", "/api/finance/vat-return", "/api/finance/payroll",
            "/api/finance/accounting/branches", "/api/finance/accounting/margins", "/api/finance/accounting/ap-ar",
            "/api/finance/accounting/expenses", "/api/autonomy/overview", "/api/autonomy/report-vs-reality",
            "/api/autonomy/shrinkage", "/api/expiry", "/api/subscription", "/api/currency",
            # revenue integrity
            "/api/revenue/overview", "/api/revenue/holds", "/api/revenue/payments?limit=15", "/api/revenue/till-log?limit=25",
            "/api/revenue/supply-breaches", "/api/revenue/carried-in",
            # multi-branch intelligence
            "/api/branches/pulse", "/api/branches/rotation", "/api/branches/comparison", "/api/branches/alerts?limit=15",
            "/api/notifications?limit=15", "/api/branches/correlations", "/api/transfers", "/api/branches/summary?limit=8",
            # expiry intelligence
            "/api/expiry/dashboard", "/api/expiry/briefing", "/api/expiry/discounts", "/api/expiry/balancing",
            "/api/expiry/forecast", "/api/expiry/orders", "/api/expiry/recalls", "/api/expiry/shelves",
            "/api/expiry/temperature", f"/api/expiry/write-offs?year={TODAY.year}&month={TODAY.month}",
            "/api/expiry/suppliers", "/api/expiry/compliance?days=30"]
MGR_EP = ["/api/dashboard", "/api/stores", "/api/inventory/counts?flagged=true&limit=30", "/api/shipments",
          "/api/attendance", "/api/employees", "/api/cameras", "/api/detections?limit=40", "/api/modes",
          "/api/money/summary", "/api/map", "/api/products", "/api/autonomy/overview",
          "/api/autonomy/report-vs-reality", "/api/expiry", "/api/subscription", "/api/currency",
          "/api/transfers", "/api/expiry/dashboard", "/api/expiry/briefing", "/api/expiry/discounts",
          "/api/expiry/balancing", "/api/expiry/forecast", "/api/expiry/orders", "/api/expiry/recalls",
          "/api/expiry/shelves", "/api/expiry/temperature", f"/api/expiry/write-offs?year={TODAY.year}&month={TODAY.month}"]

def snapshot():
    st = stores()
    out = {"owner": {}, "manager": {}}
    for ep in OWNER_EP + REPORT_EP + [f"/api/inventory?store_id={x.id}" for x in st.values()]:
        r = c.get(ep, headers=OWNER); assert r.status_code == 200, (ep, r.text); out["owner"][ep] = r.json()
    for ep in MGR_EP + [f"/api/autonomy/shift-reports/{latest[st['NBO-01'].id]}", f"/api/inventory?store_id={st['NBO-01'].id}"]:
        r = c.get(ep, headers=MGR); assert r.status_code == 200, (ep, r.text); out["manager"][ep] = r.json()
    return out

# keep the captured logins list free of the capture's own sign-ins noise? it's realistic; keep.
SCAN_EP = {"revenue": "/api/revenue/scan", "branches": "/api/branches/scan", "expiry": "/api/expiry/scan"}
scan_results = {k: c.post(ep, headers=OWNER).json() for k, ep in SCAN_EP.items()}
baseline = snapshot()
baseline["owner"]["/api/ai/scan"] = c.post("/api/ai/scan", headers=OWNER).json()
baseline["owner"]["_scan_results"] = scan_results
baseline["owner"]["_summary_templates"] = SUMMARY_TEMPLATES
with db.session() as s:
    nbo_st = s.scalars(select(Store).where(Store.code == "NBO-01")).one()
    today = frates.kenya_today()
    units = {}
    for tx in facc._sales(s, today - timedelta(days=6), today + timedelta(days=1), [nbo_st.id]):
        for i in tx.items or []:
            units[i["sku"]] = units.get(i["sku"], 0) + (-1 if tx.kind == "refund" else 1) * int(i.get("quantity", 1))
baseline["owner"]["_sales_units_nbo_7d"] = units
baseline = json.loads(json.dumps(baseline))  # plain JSON
T0 = FakeDT.now(timezone.utc).isoformat()

# ---- snapshot the database so every scenario runs from the same baseline
raw = db.engine.raw_connection()
saved = sqlite3.connect(":memory:")
raw.driver_connection.backup(saved)

SCENARIOS = [
    ("weapon", "NBO-01"), ("stock_theft", "NBO-01"), ("storekeeper_lie", "NBO-01"), ("restricted", "NBO-01"),
    ("tamper", "MBA-01"), ("off_route", "NBO-01"), ("watchlist", "KLA-01"), ("honeypot", "NBO-01"),
    ("phishing", "NBO-01"), ("cash_short", "LOS-01"), ("phone_spoof", "NBO-01"), ("refund_spree", "MBA-01"),
    ("night_intrusion", "LOS-01"), ("supplier_pin_inactive", "NBO-01"), ("sales_underreported", "NBO-01"),
    ("impersonation", "NBO-01"), ("fight", "NBO-01"), ("fall", "MBA-01"), ("crowd_surge", "NBO-01"),
    ("silent_witness", "NBO-01"), ("dead_zone", "NBO-01"), ("asset_breach", "NBO-01"), ("cross_location", "NBO-01"),
    ("expiry_disposal_fraud", "NBO-01"), ("short_delivery", "NBO-01"), ("power_cut", "KLA-01"),
    ("link_down", "NBO-01"), ("device_hot", "NBO-01"),
    # revenue integrity
    ("unregistered_sale", "NBO-01"), ("void_after_tender", "NBO-01"), ("mpesa_diverted", "NBO-01"),
    ("mpesa_orphan", "MBA-01"), ("personal_qr", "NBO-01"), ("shadow_inventory", "NBO-01"), ("ghost_sale", "NBO-01"),
    ("receipt_fraud", "NBO-01"),
    # multi-branch
    ("branch_pattern", "NBO-01"), ("transfer_short", "NBO-01"),
    # expiry intelligence
    ("chiller_fault", "NBO-01"), ("recall", "NBO-01"),
]

def key_of(ep, row):
    if "inventory?store_id" in ep and "sku" in row: return f"{row['store_id']}:{row['sku']}"
    if ep.startswith("/api/finance") or ep == "/api/products": return row.get("id", json.dumps(row, sort_keys=True))
    if "attendance" in ep: return row.get("id")
    if "cashiers" in ep: return row.get("cashier")
    if "ai/risk" in ep: return row.get("subject")
    if "ai/learning" in ep: return row.get("rule")
    if "report-vs-reality" in ep: return f"{row['kind']}|{row['store']}|{row['at']}|{row['item']}"
    if ep.startswith("/api/branches/pulse"): return row.get("store_id")
    return row["id"] if "id" in row else row.get("reference")

# The clock keeps running during capture, so ignore fields that only say when the answer was worked out,
# or that a repeat scan bumps on an alert it has already raised.
VOLATILE = {"generated_at", "local_time", "updated_at", "occurrences", "until", "since", "period", "entries_checked"}
def norm(x):
    if isinstance(x, dict): return {k: norm(v) for k, v in x.items() if k not in VOLATILE}
    if isinstance(x, list): return [norm(v) for v in x]
    return x

# Answers the page works out for itself, and the analytics whose numbers drift with the clock: only the scenarios
# that are really about that subject carry them.
PAGE_SIDE = {"/api/dashboard", "/api/modes", "/api/map", "/api/ai/learning", "/api/ai/risk"}
EXPIRY_KINDS = {"expiry_disposal_fraud", "short_delivery", "chiller_fault", "recall", "transfer_short"}
REVENUE_KINDS = {"unregistered_sale", "void_after_tender", "mpesa_diverted", "mpesa_orphan", "personal_qr", "shadow_inventory",
                 "ghost_sale", "receipt_fraud", "refund_spree", "cash_short", "branch_pattern"}
def carries(kind, ep):
    base = ep.split("?")[0]
    if base in PAGE_SIDE: return False
    if base == "/api/expiry" or (base.startswith("/api/expiry/")): return kind in EXPIRY_KINDS
    if base.startswith("/api/revenue/"): return kind in REVENUE_KINDS
    return True

def diff(before, after, kind=None):
    patch = {}
    for role in after:
        for ep, now in after[role].items():
            if kind is not None and not carries(kind, ep): continue
            was = before[role].get(ep)
            if norm(now) == norm(was): continue
            if isinstance(now, list):
                keys = [key_of(ep, r) for r in now]
                if any(k is None for k in keys):  # rows with no identity (a log, a ranking): take the whole list
                    patch.setdefault(role, {})[ep] = {"replace": now}
                    continue
                old = {key_of(ep, r): r for r in was}
                rows = [r for r in now if key_of(ep, r) not in old or norm(old[key_of(ep, r)]) != norm(r)]
                patch.setdefault(role, {})[ep] = {"upsert": rows}
            else:
                patch.setdefault(role, {})[ep] = {"replace": now}
    return patch

scenarios = {}
for kind, code in SCENARIOS:
    saved.backup(raw.driver_connection)  # restore baseline
    incident(code, kind)
    with db.session() as s:
        st = s.scalars(select(Store).where(Store.code == code)).one()
        from ojo_sentinel.engines import behaviour
        behaviour.detect_coordinated(s, st)
    intel_scan([br_mod] + ([rev_mod] if kind in REVENUE_KINDS else []) + ([exp_mod] if kind in EXPIRY_KINDS else []))
    after = json.loads(json.dumps(snapshot()))
    scenarios[kind] = {"store": code, "patch": diff(baseline, after, kind)}
    n = len(scenarios[kind]["patch"].get("owner", {}).get("/api/alerts?limit=500", {}).get("upsert", []))
    print(f"{kind:16s} {code}  alerts+{n}  endpoints={sorted(scenarios[kind]['patch'].get('owner', {}))}", file=sys.stderr)

json.dump({"t0": T0, "baseline": baseline, "scenarios": scenarios},
          open(HERE / "fixtures.json", "w"),
          separators=(",", ":"))
