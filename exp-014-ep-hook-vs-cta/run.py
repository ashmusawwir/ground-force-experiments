"""Opener A/B Comparison — Easypaisa Hook vs Easypaisa CTA.

Usage:
    cd adhoc-analysis/baseline-vs-purchase-demo
    python3 run.py                                      # sheet-only, all-time
    python3 run.py --json db_status.json               # DB-verified demos/onboardings
    python3 run.py --json db_status.json --from 2026-03-02

DB cache JSON format (from retargeting_status_query()):
    {"rows": [{"phone_number": "...", "got_demo": true, "is_onboarded": false}, ...]}
"""

import re
import csv
import json
import argparse
import urllib.request
import urllib.parse
from datetime import date, datetime, timedelta
from collections import defaultdict

# ── Constants ────────────────────────────────────────────────────────────────

SHEET_ID  = "1bFf0NAQFFXIYYxMC1yJeqowRz6MwT_-xawZeg5H9wUQ"
SHEET_TAB = "Form Responses 1"

COL_TIMESTAMP      = "Timestamp"
COL_OPENER_USED    = "Opener Used"
COL_OPENER_OUTCOME = "Opener Outcome"
COL_AMBASSADOR     = "Ambassador Name"
COL_PHONE          = "Merchant Phone"
COL_GF_AMOUNT      = "Golden Flow Amount"
COL_QR_DONE        = "QR Setup Done"

AMBASSADOR_NAMES = {
    "Arslan Ansari": "Arslan Ansari",
    "Afsar Khan":    "Afsar Khan",
    "Sharoon Sam93": "Sharoon Javed",
    "Zahid Khan":    "Muhammad Zahid",
    "Junaid Ahmed":  "Junaid Ahmed",
    "irfan rana":    "Muhammad Irfan",
    "Umer Daniyal":  "Umer Daniyal",
    "Owais Feroz":   "Owais Feroz",
    # New (added 2026-03-10)
    "muneer ahmed":  "Muneer Ahmed",
    "Ilyas Khan":    "Ilyas Khan",
    "shah comm":     "Ilyas Khan",   # same person, two form names
    "ali balouch":   "Ali Balouch",
}

OPENER_CTA   = "Easypaisa CTA"    # EXPERIMENT (opener4)
OPENER_HOOK  = "Easypaisa Hook"   # CONTROL    (opener1)
OPENER_ZAR   = "ZAR Explanation"  # opener2
OPENER_PURCH = "Purchase Demo"    # opener3
OPENER_PITCH = "Direct Pitch"     # early period
OPENER_OTHER = "Other"

HERO_CONTROL    = OPENER_HOOK
HERO_EXPERIMENT = OPENER_CTA

# Experiment metadata
OPENER_HOOK_TEXT = "You use Easypaisa, right? I help shops like yours earn extra money daily"
OPENER_CTA_TEXT  = ("You do easypaisa right? So, I help shops like yours make extra daily income "
                    "on top of what you already do. If you are free let me to show you right now?")
EXP_START_DATE   = date(2026, 3, 5)   # first CTA visit logged
TARGET_VISITS    = 100
TARGET_DEMO_RATE = 0.35

# ── Helpers ──────────────────────────────────────────────────────────────────

def classify_opener(text):
    """Classify opener text. ORDER MATTERS: CTA check before generic Easypaisa."""
    t = (text or "").strip().lower()
    if not t:
        return OPENER_OTHER
    if any(kw in t for kw in ("show you right now", "on top of what you already", "let me to show")):
        return OPENER_CTA
    if "easypaisa" in t:
        return OPENER_HOOK
    if any(kw in t for kw in ("zar card", "khareedari", "purchase")):
        return OPENER_PURCH
    if any(kw in t for kw in ("explained about zar", "zar ke baare")):
        return OPENER_ZAR
    if any(kw in t for kw in ("i help shop", "extra money", "daily income")):
        return OPENER_PITCH
    return OPENER_OTHER


def parse_timestamp(ts):
    if not ts:
        return None
    ts = ts.strip()
    result = None
    if "T" in ts:
        try:
            result = datetime.strptime(ts.split(".")[0].replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            pass
    if result is None:
        for fmt in ("%m/%d/%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S",
                    "%Y-%m-%d %H:%M:%S", "%m/%d/%Y", "%d/%m/%Y"):
            try:
                result = datetime.strptime(ts, fmt)
                break
            except ValueError:
                continue
    if result:
        result += timedelta(hours=5)  # UTC → PKT
    return result


def row_date(row):
    ts = parse_timestamp(row.get(COL_TIMESTAMP, ""))
    return ts.date() if ts else None


def ambassador_name(row):
    raw = row.get(COL_AMBASSADOR, "").strip() or "Unknown"
    return AMBASSADOR_NAMES.get(raw, raw)


def opener_passed(row):
    v = row.get(COL_OPENER_OUTCOME, "").strip().lower()
    return v not in ("not interested", "")


def is_demo(row):
    v = row.get(COL_GF_AMOUNT, "").strip().lstrip("$").strip()
    if not v or v == "0":
        return False
    try:
        return float(v) > 0
    except (ValueError, TypeError):
        return False


def is_onboarded(row):
    return row.get(COL_QR_DONE, "").strip().lower() in ("yes", "true", "done", "1", "yes")


# ── DB cache ─────────────────────────────────────────────────────────────────

def normalize_phone(raw):
    return re.sub(r'\D', '', raw or "")


def load_db_cache(path):
    """Return dict: phone (digits only) → {got_demo, is_onboarded}."""
    with open(path) as f:
        data = json.load(f)
    rows = data if isinstance(data, list) else data.get("rows", [])
    out = {}
    for r in rows:
        phone = normalize_phone(str(r.get("phone_number", "")))
        if phone:
            out[phone] = {
                "got_demo":     bool(r.get("got_demo",     False)),
                "is_onboarded": bool(r.get("is_onboarded", False)),
            }
    return out


# ── Sheet fetch ───────────────────────────────────────────────────────────────

def fetch_rows():
    tab = urllib.parse.quote(SHEET_TAB)
    url = (f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
           f"/gviz/tq?tqx=out:csv&sheet={tab}")
    with urllib.request.urlopen(url, timeout=30) as resp:
        content = resp.read().decode("utf-8")
    return list(csv.DictReader(content.splitlines()))


# ── Core computation ──────────────────────────────────────────────────────────

def build_funnel(sheet_rows, date_from, date_to, db_status=None):
    today = date.today()

    opener_buckets = defaultdict(lambda: {
        "visits": 0, "openers": 0, "demos": 0, "onboardings": 0, "dates": []
    })
    amb_buckets = defaultdict(lambda: {
        "visits": 0, "openers": 0, "demos": 0, "onboardings": 0,
        "opener_counts": defaultdict(int)
    })

    for row in sheet_rows:
        d = row_date(row)
        if not d or d >= today:
            continue
        if date_from and d < date_from:
            continue
        if date_to and d > date_to:
            continue

        opener = classify_opener(row.get(COL_OPENER_USED, ""))
        name   = ambassador_name(row)
        o      = opener_passed(row)

        if db_status:
            phone = normalize_phone(row.get(COL_PHONE, ""))
            entry = db_status.get(phone, {}) if phone else {}
            dm = entry.get("got_demo",     False)
            b  = entry.get("is_onboarded", False)
        else:
            dm = is_demo(row)
            b  = is_onboarded(row)

        opener_buckets[opener]["visits"]      += 1
        opener_buckets[opener]["openers"]     += int(o)
        opener_buckets[opener]["demos"]       += int(dm)
        opener_buckets[opener]["onboardings"] += int(b)
        opener_buckets[opener]["dates"].append(d)

        amb_buckets[name]["visits"]      += 1
        amb_buckets[name]["openers"]     += int(o)
        amb_buckets[name]["demos"]       += int(dm)
        amb_buckets[name]["onboardings"] += int(b)
        amb_buckets[name]["opener_counts"][opener] += 1

    opener_data = {}
    for label, data in opener_buckets.items():
        dates = data["dates"]
        opener_data[label] = {
            "visits":      data["visits"],
            "openers":     data["openers"],
            "demos":       data["demos"],
            "onboardings": data["onboardings"],
            "date_min":    min(dates) if dates else None,
            "date_max":    max(dates) if dates else None,
        }

    ambassador_data = []
    for name, data in sorted(amb_buckets.items()):
        top = max(data["opener_counts"], key=data["opener_counts"].get) if data["opener_counts"] else OPENER_OTHER
        ambassador_data.append({
            "name":        name,
            "top_opener":  top,
            "visits":      data["visits"],
            "openers":     data["openers"],
            "demos":       data["demos"],
            "onboardings": data["onboardings"],
            "cta_visits":  data["opener_counts"].get(OPENER_CTA, 0),
        })

    return opener_data, ambassador_data


def pct(num, den):
    if not den:
        return "—"
    return f"{round(num / den * 100)}%"


def pct_float(num, den):
    if not den:
        return None
    return num / den * 100


# ── Ambassador baseline dynamic lookback ──────────────────────────────────────

AMB_BASELINE_MIN_VISITS = 50
AMB_BASELINE_MAX_DAYS   = 90

def find_amb_baseline_start(sheet_rows, baseline_end, cta_amb_names):
    """Return the earliest baseline_start such that CTA ambassadors have
    AMB_BASELINE_MIN_VISITS combined visits up to baseline_end.
    Caps at AMB_BASELINE_MAX_DAYS before baseline_end."""
    today = date.today()
    cap   = baseline_end - timedelta(days=AMB_BASELINE_MAX_DAYS - 1)

    dates = sorted([
        row_date(row) for row in sheet_rows
        if row_date(row) is not None
        and row_date(row) < today
        and row_date(row) <= baseline_end
        and row_date(row) >= cap
        and ambassador_name(row) in cta_amb_names
    ])

    if len(dates) >= AMB_BASELINE_MIN_VISITS:
        return dates[-AMB_BASELINE_MIN_VISITS]   # date of 50th-most-recent visit
    return cap                                    # not enough data; use full cap


# ── HTML helpers ──────────────────────────────────────────────────────────────

FONTS_LINK = ('<link href="https://fonts.googleapis.com/css2?family=DM+Sans:'
              'wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">')

CSS = """
  :root {
    --gold:       #B8992E;
    --gold-light: #CBAF4A;
    --gold-dark:  #9A7E24;
    --bg:         #0D0D0D;
    --card:       #1A1A1A;
    --card-alt:   #222222;
    --border:     #2E2E2E;
    --text:       #EFEBE0;
    --muted:      #8A8680;
    --accent:     #DFD6C1;
    --green:      #16a34a;
    --red:        #dc2626;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }

  /* ── Animations ───────────────────────────────────────── */
  @keyframes fadeInUp {
    from { opacity: 0; transform: translateY(24px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  @keyframes shimmer {
    0%   { background-position: -200% center; }
    100% { background-position:  200% center; }
  }
  @keyframes pulseGold {
    0%, 100% { transform: scale(1); }
    50%       { transform: scale(1.015); }
  }
  @keyframes progressFill {
    from { width: 0; }
    to   { width: var(--target-w); }
  }

  /* ── Nav ──────────────────────────────────────────────── */
  .gf-nav {
    position: sticky; top: 0; z-index: 100;
    width: 100%; background: #0D0D0D;
    border-bottom: 1px solid #2E2E2E;
    display: flex; align-items: center;
    padding: 0.65rem 1.5rem;
  }
  .gf-nav-left  { display: flex; align-items: center; gap: 0.6rem; flex: 1; }
  .gf-nav-mid   { flex: 1; text-align: center; font-family: 'DM Sans', sans-serif;
                  font-size: 0.9rem; font-weight: 600; color: var(--accent); }
  .gf-nav-right { flex: 1; display: flex; justify-content: flex-end; align-items: center; }
  .gf-logo {
    font-family: 'DM Sans', sans-serif;
    font-size: 1rem; font-weight: 700;
    color: var(--gold-light); letter-spacing: 0.06em;
  }
  .gf-divider { color: var(--muted); font-size: 0.9rem; }
  .gf-title   { font-size: 0.85rem; color: var(--muted); font-weight: 500; }

  /* ── Page ─────────────────────────────────────────────── */
  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: var(--bg); color: var(--text);
    display: flex; flex-direction: column; align-items: center;
    padding: 0 20px 48px;
  }
  h1 {
    font-family: 'DM Sans', sans-serif;
    font-size: 1.9rem; font-weight: 700;
    color: var(--accent); margin: 1.6rem 0 6px;
  }
  .subtitle {
    font-size: 0.85rem; color: var(--muted);
    margin-bottom: 28px; text-align: center;
  }

  /* ── Cards ────────────────────────────────────────────── */
  .card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 20px; padding: 1.5rem 2rem;
    width: 100%; max-width: 980px; margin-top: 20px;
    animation: fadeInUp 0.65s cubic-bezier(0.20, 0.00, 0.15, 1.00) both;
    animation-delay: var(--delay, 0s);
  }
  .card h2 {
    font-family: 'DM Sans', sans-serif;
    font-size: 1.05rem; font-weight: 600;
    color: var(--accent); margin-bottom: 1.1rem;
    display: flex; align-items: center; gap: 0.5rem;
  }
  .num-badge {
    background: linear-gradient(90deg, var(--gold) 25%, var(--gold-light) 50%, var(--gold) 75%);
    background-size: 200% auto;
    animation: shimmer 2.5s linear infinite;
    color: #0D0D0D; width: 26px; height: 26px; border-radius: 8px;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 0.8rem; font-weight: 700; flex-shrink: 0;
  }

  /* ── Setup card ───────────────────────────────────────── */
  .setup-card { border-left: 3px solid var(--gold); background: #161616; }
  .setup-row  { display: flex; gap: 0.65rem; margin-bottom: 0.85rem; align-items: flex-start; }
  .setup-label {
    font-size: 0.72rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.09em; color: var(--muted); white-space: nowrap;
    padding-top: 0.6rem; min-width: 76px;
  }
  .setup-quote {
    background: var(--card-alt); border: 1px solid var(--border);
    border-radius: 10px; padding: 0.65rem 1rem;
    font-size: 0.84rem; color: var(--muted);
    font-style: italic; line-height: 1.6; flex: 1;
  }
  .setup-quote .cta-hl { color: var(--gold-light); font-style: normal; font-weight: 600; }
  .amb-chip {
    background: rgba(184,153,46,0.1); border: 1px solid rgba(184,153,46,0.25);
    border-radius: 100px; padding: 0.3rem 0.85rem;
    font-size: 0.8rem; color: var(--accent);
  }
  .amb-chip small { color: var(--muted); font-size: 0.72rem; }

  /* ── Status pill ──────────────────────────────────────── */
  .status-pill {
    display: inline-block; font-size: 0.65rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.1em;
    padding: 0.2rem 0.65rem; border-radius: 100px;
  }
  .pill-concluded {
    background: rgba(184,153,46,0.2); color: var(--gold-light);
    border: 1px solid rgba(184,153,46,0.4);
  }
  .pill-running {
    background: rgba(34,197,94,0.15); color: #4ade80;
    border: 1px solid rgba(34,197,94,0.35);
  }

  /* ── Progress bar ─────────────────────────────────────── */
  .progress-wrap  { display: flex; align-items: center; gap: 1rem; margin-top: 0.85rem; }
  .progress-track { flex: 1; height: 6px; background: var(--border); border-radius: 100px; overflow: hidden; }
  .progress-fill  {
    height: 100%; background: linear-gradient(90deg, var(--gold), var(--gold-light));
    border-radius: 100px;
    animation: progressFill 1s ease-out 0.4s both;
  }
  .progress-label { font-size: 0.78rem; color: var(--muted); white-space: nowrap; }

  /* ── Stat grid ────────────────────────────────────────── */
  .stat-row   { display: grid; grid-template-columns: repeat(5,1fr); gap: 0.9rem;  margin-bottom: 1.2rem; }
  .stat-row-4 { display: grid; grid-template-columns: repeat(4,1fr); gap: 0.75rem; margin-bottom: 0.9rem; }
  .stat {
    background: var(--card-alt); border: 1px solid var(--border);
    border-radius: 12px; padding: 0.9rem 0.75rem; text-align: center;
  }
  .stat-val    { font-family: 'DM Sans', sans-serif; font-size: 1.75rem; font-weight: 700; color: var(--gold-light); }
  .stat-val-sm { font-family: 'DM Sans', sans-serif; font-size: 1.25rem; font-weight: 700; color: var(--gold-light); }
  .stat-lbl    { font-size: 0.77rem; color: var(--muted); margin-top: 3px; }

  /* ── Insight strip ────────────────────────────────────── */
  .insight {
    background: rgba(184,153,46,0.07); border-left: 3px solid var(--gold);
    border-radius: 0 12px 12px 0; padding: 0.9rem 1rem;
    margin-top: 1rem; font-size: 0.85rem; color: var(--text); line-height: 1.5;
  }
  .insight strong { color: var(--gold-light); }

  /* ── Hero comparison ──────────────────────────────────── */
  .hero-box {
    background: var(--card-alt); border: 1px solid var(--border);
    border-radius: 14px; padding: 1.5rem 1.25rem;
    margin-bottom: 1.25rem; text-align: center;
  }
  .hero-lbl {
    font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.12em; color: var(--muted); margin-bottom: 1rem;
  }
  .hero-cols { display: flex; align-items: center; justify-content: center; gap: 3rem; }
  .hero-col  { text-align: center; }
  .role-pill {
    display: inline-block; font-size: 0.63rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.09em;
    padding: 0.12rem 0.5rem; border-radius: 100px; margin-bottom: 0.5rem;
  }
  .pill-control    { background: rgba(138,134,128,0.2); color: var(--muted); }
  .pill-experiment { background: rgba(184,153,46,0.2);  color: var(--gold-light); }
  .hero-val { font-family: 'DM Sans', sans-serif; font-size: 3rem; font-weight: 700; line-height: 1; }
  .winner .hero-val { color: var(--gold-light); animation: pulseGold 0.8s ease-out 0.5s both; }
  .loser  .hero-val { color: #383838; }
  .hero-name { font-size: 0.82rem; color: var(--muted); margin-top: 0.4rem; line-height: 1.4; }
  .winner .hero-name { color: var(--gold-dark); }
  .hero-vs { font-size: 0.9rem; color: var(--muted); font-weight: 500; }

  /* ── Cohort columns ───────────────────────────────────── */
  .col-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; margin-top: 1.25rem; }
  .col-pane {
    background: var(--card-alt); border: 1px solid var(--border);
    border-radius: 14px; padding: 1.1rem 1.25rem;
  }
  .col-pane h3 {
    font-family: 'DM Sans', sans-serif; font-size: 0.92rem; font-weight: 600;
    color: var(--accent); margin-bottom: 0.3rem;
  }
  .date-range { font-size: 0.72rem; color: var(--muted); margin-bottom: 0.75rem; }
  .rate-lines { font-size: 0.82rem; color: var(--muted); margin-top: 0.65rem; line-height: 2; }
  .rate-lines span { font-family: 'DM Sans', sans-serif; font-weight: 600; color: var(--accent); }
  .delta-strip {
    font-size: 0.75rem; color: var(--muted); line-height: 1.9;
    margin-top: 0.6rem; padding-top: 0.6rem; border-top: 1px solid var(--border);
  }

  /* ── Tables ───────────────────────────────────────────── */
  table { width: 100%; border-collapse: collapse; font-size: 0.84rem; }
  th {
    padding: 0.55rem 0.75rem; text-align: left;
    font-size: 0.74rem; font-weight: 500; text-transform: uppercase;
    letter-spacing: 0.05em; color: var(--muted); border-bottom: 2px solid var(--border);
  }
  th.r, td.r { text-align: right; }
  td { padding: 0.55rem 0.75rem; border-bottom: 1px solid var(--border); color: var(--text); }
  td.r { font-family: 'DM Sans', sans-serif; font-weight: 600; color: var(--accent); }
  td.delta { text-align: right; font-size: 0.8rem; }
  tr:last-child td { border-bottom: none; }
  tr.tot td {
    font-weight: 700; background: rgba(184,153,46,0.05);
    border-top: 1px solid var(--border); border-bottom: none; color: var(--gold-light);
  }
  tr.tot td.r { color: var(--gold-light); }

  /* ── Opener badge ─────────────────────────────────────── */
  .badge {
    display: inline-block; padding: 0.12rem 0.45rem;
    border-radius: 100px; font-size: 0.68rem; font-weight: 600; vertical-align: middle;
  }
  .b-hook  { background: rgba(138,134,128,0.18); color: var(--muted); }
  .b-cta   { background: rgba(184,153,46,0.22);  color: var(--gold-light); }
  .b-zar   { background: rgba(22,163,74,0.15);   color: #4ade80; }
  .b-purch { background: rgba(59,130,246,0.15);  color: #93c5fd; }
  .b-pitch { background: rgba(99,102,241,0.15);  color: #a5b4fc; }
  .b-other { background: rgba(107,107,107,0.12); color: var(--muted); }

  /* ── Recommendation card ──────────────────────────────── */
  .rec-card-adopt  { border-left: 3px solid #16a34a; background: #111a13; }
  .rec-card-reject { border-left: 3px solid #dc2626; background: #1a1111; }
  .rec-card-ambig  { border-left: 3px solid var(--gold); background: #161612; }
  .pill-adopt { background: rgba(22,163,74,0.2);  color: #4ade80; border: 1px solid rgba(22,163,74,0.4); }
  .pill-reject{ background: rgba(220,38,38,0.2);  color: #f87171; border: 1px solid rgba(220,38,38,0.4); }
  .pill-ambig { background: rgba(184,153,46,0.2); color: var(--gold-light); border: 1px solid rgba(184,153,46,0.4); }
  .rec-decision-pill {
    display: inline-block; font-size: 1rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.1em;
    padding: 0.35rem 1.2rem; border-radius: 100px; margin-bottom: 1.1rem;
  }
  .rec-reasoning {
    font-size: 0.87rem; color: var(--muted); line-height: 1.7; margin-bottom: 1.1rem;
  }
  .rec-reasoning strong { color: var(--accent); }

  footer { margin-top: 32px; font-size: 0.73rem; color: var(--muted); }

  @media (max-width: 640px) {
    .stat-row   { grid-template-columns: repeat(3,1fr); }
    .stat-row-4 { grid-template-columns: repeat(2,1fr); }
    .col-grid   { grid-template-columns: 1fr; }
    .period-grid { grid-template-columns: 1fr; }
  }
"""

COUNTER_JS = """
<script>
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('[data-count]').forEach(function(el) {
    var target = parseFloat(el.dataset.count);
    if (isNaN(target)) return;
    var suffix = el.dataset.suffix || '';
    var duration = 700;
    var startTime = null;
    function tick(now) {
      if (!startTime) startTime = now;
      var t = Math.min((now - startTime) / duration, 1);
      var eased = 1 - Math.pow(1 - t, 3);
      el.textContent = Math.round(eased * target).toLocaleString() + suffix;
      if (t < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  });
});
</script>
"""


def _stat(val, lbl, sm=False):
    cls = "stat-val-sm" if sm else "stat-val"
    return f'<div class="stat"><div class="{cls}">{val}</div><div class="stat-lbl">{lbl}</div></div>'


def _stat_count(num, lbl, sm=False):
    cls = "stat-val-sm" if sm else "stat-val"
    return (f'<div class="stat">'
            f'<div class="{cls}" data-count="{num}" data-suffix="">{num:,}</div>'
            f'<div class="stat-lbl">{lbl}</div></div>')


def _badge(opener):
    cls_map   = {OPENER_HOOK:"b-hook", OPENER_CTA:"b-cta", OPENER_ZAR:"b-zar",
                 OPENER_PURCH:"b-purch", OPENER_PITCH:"b-pitch"}
    short_map = {OPENER_HOOK:"EP Hook", OPENER_CTA:"EP CTA", OPENER_ZAR:"ZAR Expl.",
                 OPENER_PURCH:"Purchase", OPENER_PITCH:"Direct", OPENER_OTHER:"Other"}
    return f'<span class="badge {cls_map.get(opener,"b-other")}">{short_map.get(opener,opener)}</span>'


def _delta_html(exp_val, base_val):
    """Colored delta for two float percentages. Returns HTML span."""
    if exp_val is None or base_val is None:
        return '<span style="color:var(--muted)">—</span>'
    diff = exp_val - base_val
    if abs(diff) < 0.5:
        return '<span style="color:var(--muted)">≈</span>'
    mag = round(abs(diff))
    if diff > 0:
        return f'<span style="color:#4ade80">&#9650;{mag}pp</span>'
    return f'<span style="color:#f87171">&#9660;{mag}pp</span>'


# ── Card 1: Experiment Setup ──────────────────────────────────────────────────

def experiment_setup_card(cta_ambassadors, cta_visits_total):
    progress_pct = min(cta_visits_total / TARGET_VISITS * 100, 100)

    cta_highlighted = OPENER_CTA_TEXT.replace(
        "If you are free let me to show you right now?",
        '<span class="cta-hl">If you are free let me to show you right now?</span>'
    )

    return f"""<div class="card setup-card" style="--delay:0.05s">
  <h2><span class="num-badge">1</span> Experiment Setup</h2>
  <div style="font-size:0.82rem;color:var(--muted);margin-bottom:1rem;line-height:1.6">
    <strong style="color:var(--accent)">What&#39;s being tested:</strong>
    Does adding an explicit call-to-action (&ldquo;let me show you right now&rdquo;)
    to the Easypaisa hook increase demo conversion versus the plain hook?
  </div>
  <div class="setup-row">
    <div class="setup-label">Control</div>
    <div class="setup-quote">{OPENER_HOOK_TEXT}</div>
  </div>
  <div class="setup-row">
    <div class="setup-label">Experiment</div>
    <div class="setup-quote" style="color:var(--accent)">{cta_highlighted}</div>
  </div>
  <div class="progress-wrap">
    <div class="progress-track">
      <div class="progress-fill" style="--target-w:{progress_pct:.1f}%"></div>
    </div>
    <div class="progress-label">{cta_visits_total} / {TARGET_VISITS} CTA visits</div>
  </div>
</div>"""


# ── Card 2: Recommendation ───────────────────────────────────────────────────

def recommendation_card(opener_data):
    hook = opener_data.get(HERO_CONTROL,    {"visits":0,"openers":0,"demos":0,"onboardings":0})
    cta  = opener_data.get(HERO_EXPERIMENT, {"visits":0,"openers":0,"demos":0,"onboardings":0})

    hook_yield  = pct_float(hook["onboardings"], hook["visits"])
    cta_yield   = pct_float(cta["onboardings"],  cta["visits"])
    hook_demo   = pct_float(hook["demos"],  hook["openers"])
    cta_demo    = pct_float(cta["demos"],   cta["openers"])
    hook_opener = pct_float(hook["openers"], hook["visits"])
    cta_opener  = pct_float(cta["openers"],  cta["visits"])

    # Decision — based on opener rate + demo rate (not yield)
    if (cta_opener or 0) >= (hook_opener or 0) and (cta_demo or 0) >= (hook_demo or 0):
        decision, pill_cls, card_cls = "ADOPT CTA",        "pill-adopt", "rec-card-adopt"
    elif (cta_opener or 0) < (hook_opener or 0) and (cta_demo or 0) < (hook_demo or 0):
        decision, pill_cls, card_cls = "DO NOT ADOPT CTA", "pill-reject", "rec-card-reject"
    else:
        decision, pill_cls, card_cls = "INCONCLUSIVE",     "pill-ambig",  "rec-card-ambig"

    # Auto-generated reasoning
    opener_delta = round((cta_opener or 0) - (hook_opener or 0))
    demo_delta   = round((cta_demo   or 0) - (hook_demo   or 0))
    sign = lambda d: f"+{d}pp" if d >= 0 else f"{d}pp"

    if decision == "ADOPT CTA":
        line1 = (f"CTA outperformed on both metrics: opener rate {sign(opener_delta)} "
                 f"({round(cta_opener or 0)}% vs {round(hook_opener or 0)}%) and demo rate "
                 f"{sign(demo_delta)} ({round(cta_demo or 0)}% vs {round(hook_demo or 0)}%).")
        line2 = "Switch to <strong>Easypaisa CTA</strong> as the default opener."
    elif decision == "DO NOT ADOPT CTA":
        line1 = (f"Hook outperformed on both metrics: opener rate {sign(-opener_delta)} "
                 f"and demo rate {sign(-demo_delta)} vs CTA.")
        line2 = "Keep <strong>Easypaisa Hook</strong> as the default opener."
    else:
        line1 = (f"Mixed results: opener rate {sign(opener_delta)}, demo rate {sign(demo_delta)}. "
                 f"Neither opener consistently outperforms on both dimensions.")
        line2 = "Collect more CTA data before concluding — sample size is below target."

    opener_color = "#4ade80" if opener_delta >= 0 else "#f87171"
    demo_color   = "#4ade80" if demo_delta   >= 0 else "#f87171"
    sign_str = lambda d: f"+{d}pp" if d >= 0 else f"{d}pp"

    tiles = (
        f'<div class="stat-row-4" style="grid-template-columns:repeat(2,1fr)">'
        f'<div class="stat"><div class="stat-val" style="color:{opener_color}">'
        f'{sign_str(opener_delta)}</div>'
        f'<div class="stat-lbl">&Delta; Opener Rate</div></div>'
        f'<div class="stat"><div class="stat-val" style="color:{demo_color}">'
        f'{sign_str(demo_delta)}</div>'
        f'<div class="stat-lbl">&Delta; Demo Rate</div></div>'
        f'</div>'
    )

    return (
        f'<div class="card {card_cls}" style="--delay:0.13s">'
        f'<h2><span class="num-badge">2</span> Recommendation</h2>'
        f'<span class="rec-decision-pill status-pill {pill_cls}">{decision}</span>'
        f'<div class="rec-reasoning">{line1}<br><br>{line2}</div>'
        f'{tiles}'
        f'</div>'
    )


# ── Card 3: Verdict ───────────────────────────────────────────────────────────

def _metric_hero(title, definition, ctrl_pct, ctrl_sub, exp_pct, exp_sub, exp_wins):
    """Single-metric hero box comparing Hook (control) vs CTA (experiment)."""
    ctrl_cls = "hero-col loser"  if exp_wins else "hero-col winner"
    exp_cls  = "hero-col winner" if exp_wins else "hero-col loser"
    ctrl_r = round(ctrl_pct or 0)
    exp_r  = round(exp_pct  or 0)
    ctrl_attr = f' data-count="{ctrl_r}" data-suffix="%"'
    exp_attr  = f' data-count="{exp_r}"  data-suffix="%"'
    return (
        f'<div class="hero-box" style="margin-bottom:0;flex:1">'
        f'<div class="hero-lbl">{title} &mdash; <em>{definition}</em></div>'
        f'<div class="hero-cols">'
        f'<div class="{ctrl_cls}"><div class="role-pill pill-control">CONTROL</div>'
        f'<div class="hero-val"{ctrl_attr}>{ctrl_r}%</div>'
        f'<div class="hero-name">Easypaisa Hook<br>'
        f'<small style="font-size:0.7rem;color:var(--muted)">{ctrl_sub}</small></div></div>'
        f'<div class="hero-vs">vs</div>'
        f'<div class="{exp_cls}"><div class="role-pill pill-experiment">EXPERIMENT</div>'
        f'<div class="hero-val"{exp_attr}>{exp_r}%</div>'
        f'<div class="hero-name">Easypaisa CTA<br>'
        f'<small style="font-size:0.7rem;color:var(--muted)">{exp_sub}</small></div></div>'
        f'</div></div>'
    )


def verdict_card(opener_data, baseline_opener_data=None):
    ctrl = opener_data.get(HERO_CONTROL,    {"visits":0,"openers":0,"demos":0,"onboardings":0})
    exp  = opener_data.get(HERO_EXPERIMENT, {"visits":0,"openers":0,"demos":0,"onboardings":0})

    ctrl_opener = pct_float(ctrl["openers"], ctrl["visits"])
    exp_opener  = pct_float(exp["openers"],  exp["visits"])
    ctrl_demo   = pct_float(ctrl["demos"],   ctrl["openers"])
    exp_demo    = pct_float(exp["demos"],    exp["openers"])

    opener_exp_wins = (exp_opener or 0) >= (ctrl_opener or 0)
    demo_exp_wins   = (exp_demo   or 0) >= (ctrl_demo   or 0)

    hero1 = _metric_hero(
        "Opener Rate", "visits where conversation started",
        ctrl_opener, f"{ctrl['visits']:,} visits",
        exp_opener,  f"{exp['visits']:,} visits", opener_exp_wins)
    hero2 = _metric_hero(
        "Demo Rate", "openers who saw the app",
        ctrl_demo, f"{ctrl['openers']:,} openers",
        exp_demo,  f"{exp['openers']:,} openers", demo_exp_wins)

    hero_html = f'<div style="display:flex;gap:1rem;margin-bottom:1rem">{hero1}{hero2}</div>'

    opener_delta = round((exp_opener or 0) - (ctrl_opener or 0))
    demo_delta   = round((exp_demo   or 0) - (ctrl_demo   or 0))
    sign = lambda d: f"+{d}pp" if d >= 0 else f"{d}pp"
    callout = (
        f"CTA: opener rate {sign(opener_delta)}, demo rate {sign(demo_delta)}"
        f" &nbsp;&middot;&nbsp; <em style='color:var(--muted)'>{exp['visits']:,} CTA visits logged</em>"
    )

    return (
        f'<div class="card" style="--delay:0.20s">'
        f'<h2><span class="num-badge">3</span> Verdict</h2>'
        f'{hero_html}'
        f'<div class="insight">{callout}</div>'
        f'<div class="col-grid">'
        f'{_cohort_pane("Easypaisa Hook", ctrl, None)}'
        f'{_cohort_pane("Easypaisa CTA",  exp,  ctrl)}'
        f'</div>'
        f'</div>'
    )


def _cohort_pane(label, data, baseline=None):
    v  = data["visits"]; o  = data["openers"]
    d  = data["demos"];  b  = data["onboardings"]
    dt_min = data.get("date_min"); dt_max = data.get("date_max")
    dr = ""
    if dt_min and dt_max:
        dr = f'<div class="date-range">{dt_min.strftime("%b %-d")} &ndash; {dt_max.strftime("%b %-d")}</div>'

    delta_html = ""
    if baseline:
        bv = baseline["visits"]; bo = baseline["openers"]
        bd = baseline["demos"];  bb = baseline["onboardings"]
        delta_html = (
            f'<div class="delta-strip">'
            f'Opener Rate vs EP Hook: {_delta_html(pct_float(o,v), pct_float(bo,bv))}<br>'
            f'Demo Rate vs EP Hook: {_delta_html(pct_float(d,o), pct_float(bd,bo))}<br>'
            f'Overall Yield vs EP Hook: {_delta_html(pct_float(b,v), pct_float(bb,bv))}'
            f'</div>'
        )

    return (
        f'<div class="col-pane">'
        f'<h3>{label}</h3>{dr}'
        f'<div class="stat-row-4">'
        f'{_stat(f"{v:,}", "Visits", sm=True)}'
        f'{_stat(f"{o:,}", "Openers", sm=True)}'
        f'{_stat(f"{d:,}", "Demos", sm=True)}'
        f'{_stat(f"{b:,}", "Onboardings", sm=True)}'
        f'</div>'
        f'<div class="rate-lines">'
        f'Opener Rate &nbsp;<span>{pct(o,v)}</span><br>'
        f'Demo Rate &nbsp;<span>{pct(d,o)}</span><br>'
        f'Onboarding Rate &nbsp;<span>{pct(b,d)}</span><br>'
        f'Overall Yield &nbsp;<span>{pct(b,v)}</span>'
        f'</div>'
        f'{delta_html}'
        f'</div>'
    )


# ── Card 4: Opener vs Baseline ────────────────────────────────────────────────

def opener_baseline_card(exp_opener_data, baseline_opener_data,
                         exp_start, exp_end, baseline_start, baseline_end):
    _npd = '<td colspan="2" style="color:var(--muted);font-size:0.78rem;text-align:center;font-style:italic">no prior data</td>'
    rows_html = ""
    for label in [OPENER_HOOK, OPENER_CTA]:
        exp  = exp_opener_data.get(label,      {"visits":0,"openers":0,"demos":0,"onboardings":0})
        base = baseline_opener_data.get(label, {"visits":0,"openers":0,"demos":0,"onboardings":0})
        ev = exp["visits"];  eo = exp["openers"];  ed = exp["demos"];  eb = exp["onboardings"]
        bv = base["visits"]; bo = base["openers"]; bd = base["demos"]; bb = base["onboardings"]
        if bv == 0:
            rows_html += (
                f'<tr>'
                f'<td>{_badge(label)} {label}</td>'
                f'<td class="r">{ev:,}</td>'
                f'<td class="r">{pct(eo,ev)}</td>'
                f'{_npd}'
                f'<td class="r">{pct(ed,eo)}</td>'
                f'{_npd}'
                f'</tr>'
            )
        else:
            rows_html += (
                f'<tr>'
                f'<td>{_badge(label)} {label}</td>'
                f'<td class="r">{ev:,}</td>'
                f'<td class="r">{pct(eo,ev)}</td>'
                f'<td class="r">{pct(bo,bv)}</td>'
                f'<td class="delta">{_delta_html(pct_float(eo,ev), pct_float(bo,bv))}</td>'
                f'<td class="r">{pct(ed,eo)}</td>'
                f'<td class="r">{pct(bd,bo)}</td>'
                f'<td class="delta">{_delta_html(pct_float(ed,eo), pct_float(bd,bo))}</td>'
                f'</tr>'
            )

    exp_lbl  = f"{exp_start.strftime('%b %-d')} &ndash; {exp_end.strftime('%b %-d')}"
    base_lbl = f"{baseline_start.strftime('%b %-d')} &ndash; {baseline_end.strftime('%b %-d')}"

    return (
        f'<div class="card" style="--delay:0.30s">'
        f'<h2><span class="num-badge">4</span> Opener vs Baseline</h2>'
        f'<div style="font-size:0.78rem;color:var(--muted);margin-bottom:0.9rem">'
        f'Experiment: {exp_lbl} &nbsp;&middot;&nbsp; Baseline: {base_lbl}</div>'
        f'<table><thead><tr>'
        f'<th>Opener</th><th class="r">Visits</th>'
        f'<th class="r">Opener% (exp)</th><th class="r">Opener% (base)</th><th class="r">&Delta;</th>'
        f'<th class="r">Demo% (exp)</th><th class="r">Demo% (base)</th><th class="r">&Delta;</th>'
        f'</tr></thead><tbody>{rows_html}</tbody></table>'
        f'</div>'
    )


# ── Card 5: Ambassador Baseline ───────────────────────────────────────────────

def ambassador_baseline_card(cta_ambassadors, exp_amb_data, baseline_amb_data,
                              exp_start, exp_end, baseline_start, baseline_end):
    exp_by_name  = {a["name"]: a for a in exp_amb_data}
    base_by_name = {a["name"]: a for a in baseline_amb_data}

    exp_lbl  = f"{exp_start.strftime('%b %-d')} &ndash; {exp_end.strftime('%b %-d')}"
    base_lbl = f"{baseline_start.strftime('%b %-d')} &ndash; {baseline_end.strftime('%b %-d')} (auto-extended)"

    EMPTY = {"visits":0,"openers":0,"demos":0,"onboardings":0}
    blocks = ""
    for i, a in enumerate(cta_ambassadors):
        name = a["name"]
        base = base_by_name.get(name, EMPTY)
        exp  = exp_by_name.get(name, EMPTY)
        bv = base["visits"]; bo = base["openers"]; bd = base["demos"]; bb = base["onboardings"]
        ev = exp["visits"];  eo = exp["openers"];  ed = exp["demos"];  eb = exp["onboardings"]

        mb = "" if i == len(cta_ambassadors) - 1 else "margin-bottom:1.5rem;padding-bottom:1.5rem;border-bottom:1px solid var(--border);"

        blocks += (
            f'<div style="{mb}">'
            f'<div style="font-size:0.88rem;font-weight:600;color:var(--accent);margin-bottom:0.75rem">{name}</div>'
            f'<div class="col-grid">'
            f'<div class="col-pane">'
            f'<h3>Baseline</h3>'
            f'<div class="date-range">{base_lbl}</div>'
            f'<div class="stat-row-4" style="grid-template-columns:repeat(3,1fr)">'
            f'{_stat(f"{bv:,}", "Visits", sm=True)}'
            f'{_stat(pct(bo, bv), "Opener%", sm=True)}'
            f'{_stat(pct(bd, bo), "Demo%", sm=True)}'
            f'</div>'
            f'</div>'
            f'<div class="col-pane" style="border-color:rgba(184,153,46,0.35)">'
            f'<h3>Experiment</h3>'
            f'<div class="date-range">{exp_lbl}</div>'
            f'<div class="stat-row-4" style="grid-template-columns:repeat(3,1fr)">'
            f'{_stat(f"{ev:,}", "Visits", sm=True)}'
            f'{_stat(pct(eo, ev), "Opener%", sm=True)}'
            f'{_stat(pct(ed, eo), "Demo%", sm=True)}'
            f'</div>'
            f'</div>'
            f'</div>'
            f'<div class="delta-strip" style="padding:0.55rem 0.25rem 0;margin-top:0.75rem">'
            f'&Delta; Opener%: {_delta_html(pct_float(eo,ev), pct_float(bo,bv))}'
            f' &nbsp;&nbsp;&middot;&nbsp;&nbsp; '
            f'&Delta; Demo%: {_delta_html(pct_float(ed,eo), pct_float(bd,bo))}'
            f'</div>'
            f'</div>'
        )

    return (
        f'<div class="card" style="--delay:0.30s">'
        f'<h2><span class="num-badge">4</span> Ambassador Baseline</h2>'
        f'{blocks}'
        f'</div>'
    )


# ── HTML assembly ─────────────────────────────────────────────────────────────

def generate_html(opener_data, exp_opener_data, baseline_opener_data,
                  ambassador_data, exp_amb_data, baseline_amb_data,
                  cta_ambassadors,
                  date_from, date_to,
                  exp_start, exp_end, baseline_start, baseline_end, amb_baseline_start,
                  db_mode=False):
    run_dt     = datetime.now().strftime("%Y-%m-%d %H:%M PKT")
    window_str = (f"{date_from.strftime('%b %-d')} &ndash; {date_to.strftime('%b %-d')}"
                  if date_from else "All time")
    data_source = "DB-verified" if db_mode else "sheet self-report"
    tot_v = sum(d["visits"] for d in opener_data.values())

    cta_visits_total = (exp_opener_data or opener_data).get(OPENER_CTA, {"visits":0})["visits"]

    card1 = experiment_setup_card(cta_ambassadors, cta_visits_total)
    card2 = recommendation_card(opener_data)
    card3 = verdict_card(opener_data, baseline_opener_data)

    card4 = ""
    if (baseline_amb_data is not None and exp_amb_data is not None and cta_ambassadors):
        card4 = ambassador_baseline_card(cta_ambassadors, exp_amb_data, baseline_amb_data,
                                         exp_start, exp_end, amb_baseline_start, baseline_end)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Opener A/B &mdash; ZAR Ground Force</title>
{FONTS_LINK}
<style>{CSS}</style>
</head>
<body>
<nav class="gf-nav">
  <div class="gf-nav-left">
    <span class="gf-logo">ZAR</span>
    <span class="gf-divider">&middot;</span>
    <span class="gf-title">Ground Force Experiments</span>
  </div>
  <div class="gf-nav-mid">EP CTA opener outperforms EP hook on both opener conversion rate and demo rate</div>
  <div class="gf-nav-right">
    <span class="status-pill pill-running">IN PROGRESS</span>
  </div>
</nav>
<div class="subtitle">
  Easypaisa Hook (control) vs Easypaisa CTA (experiment)
  &nbsp;&middot;&nbsp; {window_str}
  &nbsp;&middot;&nbsp; {tot_v:,} total visits
  &nbsp;&middot;&nbsp; demos/onboardings: {data_source}
</div>
{card1}
{card2}
{card3}
{card4}
<footer>Generated {run_dt} &nbsp;&middot;&nbsp; Sheet {SHEET_ID}</footer>
{COUNTER_JS}
</body>
</html>"""


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    today = date.today()

    parser = argparse.ArgumentParser(description="Opener A/B comparison report")
    parser.add_argument("--json", metavar="PATH",
                        help="DB cache JSON (phone→got_demo/is_onboarded)")
    parser.add_argument("--from", dest="date_from", metavar="YYYY-MM-DD", default=None,
                        help="Filter start date (enables baseline cards)")
    parser.add_argument("--to", dest="date_to", metavar="YYYY-MM-DD", default=None,
                        help="Filter end date (default: yesterday)")
    args = parser.parse_args()

    date_from = date.fromisoformat(args.date_from) if args.date_from else None
    date_to   = date.fromisoformat(args.date_to)   if args.date_to   else today - timedelta(days=1)

    print("Fetching sheet...")
    sheet_rows = fetch_rows()
    print(f"  {len(sheet_rows)} rows fetched")

    db_status = {}
    if args.json:
        print(f"Loading DB cache from {args.json}...")
        db_status = load_db_cache(args.json)
        print(f"  {len(db_status)} phones in DB cache")
    else:
        print("No --json flag — using sheet columns for demo/onboarding")

    # Main funnel (filtered window)
    opener_data, ambassador_data = build_funnel(sheet_rows, date_from, date_to, db_status)

    # Experiment-window funnel (EXP_START_DATE → date_to): CTA ambassador detection + Card 3
    exp_start = EXP_START_DATE
    exp_end   = date_to
    exp_opener_data, exp_amb_data = build_funnel(sheet_rows, exp_start, exp_end, db_status)

    # Top-2 CTA ambassadors by CTA visits in experiment window
    cta_ambassadors = sorted(
        [a for a in exp_amb_data if a.get("cta_visits", 0) > 0],
        key=lambda x: -x["cta_visits"]
    )

    # Baseline window (only when --from is set)
    baseline_opener_data = baseline_amb_data = None
    baseline_start = baseline_end = amb_baseline_start = None
    if date_from:
        lookback_days  = (exp_end - exp_start).days + 1
        baseline_end   = exp_start - timedelta(days=1)
        baseline_start = baseline_end - timedelta(days=lookback_days - 1)
        baseline_opener_data, _ = build_funnel(
            sheet_rows, baseline_start, baseline_end, db_status
        )
        print(f"  Baseline window: {baseline_start} – {baseline_end} ({lookback_days} days)")

        # Separate, extended ambassador baseline for Card 5
        cta_amb_names   = {a["name"] for a in cta_ambassadors}
        amb_baseline_start = find_amb_baseline_start(sheet_rows, baseline_end, cta_amb_names)
        _, baseline_amb_data = build_funnel(sheet_rows, amb_baseline_start, baseline_end, db_status)
        print(f"  Amb baseline: {amb_baseline_start} – {baseline_end} "
              f"({(baseline_end - amb_baseline_start).days + 1} days)")

    # Terminal output
    ORDER = [OPENER_CTA, OPENER_HOOK, OPENER_ZAR, OPENER_PURCH, OPENER_PITCH, OPENER_OTHER]
    print(f"\n{'Opener':<20} {'Visits':>7}  {'Opener%':>8}  {'Demo%':>7}  {'Yield':>6}  {'Dates'}")
    print("-" * 75)
    tot = {"visits":0,"openers":0,"demos":0,"onboardings":0}
    for label in ORDER:
        data = opener_data.get(label)
        if not data or data["visits"] == 0:
            continue
        v = data["visits"]; o = data["openers"]; d = data["demos"]; b = data["onboardings"]
        tot["visits"] += v; tot["openers"] += o; tot["demos"] += d; tot["onboardings"] += b
        dr = ""
        if data.get("date_min") and data.get("date_max"):
            dr = f"{data['date_min'].strftime('%b %-d')} – {data['date_max'].strftime('%b %-d')}"
        print(f"{label:<20} {v:>7,}  {pct(o,v):>8}  {pct(d,o):>7}  {pct(b,v):>6}  {dr}")
    print("-" * 75)
    print(f"{'TOTAL':<20} {tot['visits']:>7,}  {pct(tot['openers'],tot['visits']):>8}  "
          f"{pct(tot['demos'],tot['openers']):>7}  {pct(tot['onboardings'],tot['visits']):>6}")

    out = "opener_comparison.html"
    with open(out, "w") as f:
        f.write(generate_html(
            opener_data, exp_opener_data, baseline_opener_data,
            ambassador_data, exp_amb_data, baseline_amb_data,
            cta_ambassadors,
            date_from, date_to,
            exp_start, exp_end, baseline_start, baseline_end, amb_baseline_start,
            db_mode=bool(db_status)
        ))
    print(f"\nHTML written → {out}")


if __name__ == "__main__":
    main()
