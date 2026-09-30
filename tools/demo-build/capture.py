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

app = create_app(Settings(database_url="sqlite://", seed_demo=True, finance_scan_minutes=0, autonomy_scan_minutes=0))
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

def incident(code, kind):
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

OWNER_EP = ["/api/dashboard", "/api/stores", "/api/alerts?limit=500", "/api/inventory/counts?flagged=true&limit=30",
            "/api/shipments", "/api/attendance", "/api/employees", "/api/assets", "/api/phones", "/api/modes",
            "/api/cameras", "/api/detections?limit=40", "/api/honeypot/tokens", "/api/honeypot/hits",
            "/api/cyber/email/scans", "/api/cyber/logins", "/api/money/summary", "/api/money/cashiers",
            "/api/money/benford", "/api/ai/risk", "/api/ai/learning", "/api/audit?limit=200", "/api/map",
            "/api/products", "/api/finance/overview", "/api/finance/vat-return", "/api/finance/payroll",
            "/api/finance/accounting/branches", "/api/finance/accounting/margins", "/api/finance/accounting/ap-ar",
            "/api/finance/accounting/expenses", "/api/autonomy/overview", "/api/autonomy/report-vs-reality",
            "/api/autonomy/shrinkage", "/api/expiry", "/api/subscription", "/api/currency"]
MGR_EP = ["/api/dashboard", "/api/stores", "/api/inventory/counts?flagged=true&limit=30", "/api/shipments",
          "/api/attendance", "/api/employees", "/api/cameras", "/api/detections?limit=40", "/api/modes",
          "/api/money/summary", "/api/map", "/api/products", "/api/autonomy/overview",
          "/api/autonomy/report-vs-reality", "/api/expiry", "/api/subscription", "/api/currency"]

def snapshot():
    st = stores()
    out = {"owner": {}, "manager": {}}
    for ep in OWNER_EP + REPORT_EP + [f"/api/inventory?store_id={x.id}" for x in st.values()]:
        r = c.get(ep, headers=OWNER); assert r.status_code == 200, (ep, r.text); out["owner"][ep] = r.json()
    for ep in MGR_EP + [f"/api/autonomy/shift-reports/{latest[st['NBO-01'].id]}", f"/api/inventory?store_id={st['NBO-01'].id}"]:
        r = c.get(ep, headers=MGR); assert r.status_code == 200, (ep, r.text); out["manager"][ep] = r.json()
    return out

# keep the captured logins list free of the capture's own sign-ins noise? it's realistic; keep.
baseline = snapshot()
baseline["owner"]["/api/ai/scan"] = c.post("/api/ai/scan", headers=OWNER).json()
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
]

def key_of(ep, row):
    if "inventory?store_id" in ep and "sku" in row: return f"{row['store_id']}:{row['sku']}"
    if ep.startswith("/api/finance") or ep == "/api/products": return row.get("id", json.dumps(row, sort_keys=True))
    if "attendance" in ep: return row.get("id")
    if "cashiers" in ep: return row.get("cashier")
    if "ai/risk" in ep: return row.get("subject")
    if "ai/learning" in ep: return row.get("rule")
    if "report-vs-reality" in ep: return f"{row['kind']}|{row['store']}|{row['at']}|{row['item']}"
    return row.get("id")

def diff(before, after):
    patch = {}
    for role in after:
        for ep, now in after[role].items():
            was = before[role].get(ep)
            if now == was: continue
            if isinstance(now, list):
                old = {key_of(ep, r): r for r in was}
                rows = [r for r in now if key_of(ep, r) not in old or old[key_of(ep, r)] != r]
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
    after = json.loads(json.dumps(snapshot()))
    scenarios[kind] = {"store": code, "patch": diff(baseline, after)}
    n = len(scenarios[kind]["patch"].get("owner", {}).get("/api/alerts?limit=500", {}).get("upsert", []))
    print(f"{kind:16s} {code}  alerts+{n}  endpoints={sorted(scenarios[kind]['patch'].get('owner', {}))}", file=sys.stderr)

json.dump({"t0": T0, "baseline": baseline, "scenarios": scenarios},
          open(HERE / "fixtures.json", "w"),
          separators=(",", ":"))
