"""EP-Referred vs Legacy Contractor Funnel — entry point.

Usage:
    cd adhoc-analysis/old-vs-new-ambassadors
    python3 run.py --json <db_cache.json>
    python3 run.py --json <db_cache.json> --from 2026-02-16 --to 2026-03-05

Defaults: --from = last week Monday, --to = yesterday.

The DB cache JSON must have a "rows" array where each item has:
    phone_number, got_demo, is_onboarded
(produced by retargeting_status_query() via Metabase/Rube MCP).
"""

import sys
import os
import json
import re
import csv
import urllib.request
import urllib.parse
import argparse
from datetime import date, datetime, timedelta
from collections import defaultdict

# ── Constants ────────────────────────────────────────────────────────────────

SHEET_ID   = "1bFf0NAQFFXIYYxMC1yJeqowRz6MwT_-xawZeg5H9wUQ"
SHEET_TAB  = "Form Responses 1"

COL_TIMESTAMP      = "Timestamp"
COL_OPENER_OUTCOME = "Opener Outcome"
COL_AMBASSADOR     = "Ambassador Name"
COL_PHONE          = "Merchant Phone"

AMBASSADOR_NAMES = {
    "Arslan Ansari":  "Arslan Ansari",
    "Afsar Khan":     "Afsar Khan",
    "Sharoon Sam93":  "Sharoon Javed",
    "Zahid Khan":     "Muhammad Zahid",
    "Junaid Ahmed":   "Junaid Ahmed",
    "irfan rana":     "Muhammad Irfan",
    "Umer Daniyal":   "Umer Daniyal",
    "Owais Feroz":    "Owais Feroz",
}

NEW_CUTOFF = date(2026, 2, 23)   # first visit >= this date → "New" (EP-Referred)

# Contractors who are EP-referred regardless of first visit date
EP_REFERRED_OVERRIDE = {"Owais Feroz", "Umer Daniyal"}

COHORT_LABEL = {"New": "EP-Referred", "Old": "Legacy"}

# ── Helpers ──────────────────────────────────────────────────────────────────

def normalize_phone(raw):
    return re.sub(r'\D', '', raw or "")


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
        result += timedelta(hours=5)   # UTC → PKT
    return result


def row_date(row):
    ts = parse_timestamp(row.get(COL_TIMESTAMP, ""))
    return ts.date() if ts else None


def ambassador_name(row):
    raw = row.get(COL_AMBASSADOR, "").strip() or "Unknown"
    return AMBASSADOR_NAMES.get(raw, raw)


def opener_passed(row):
    return row.get(COL_OPENER_OUTCOME, "").strip().lower() != "not interested"


# ── Sheet fetch ───────────────────────────────────────────────────────────────

def fetch_rows():
    tab = urllib.parse.quote(SHEET_TAB)
    url = (f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
           f"/gviz/tq?tqx=out:csv&sheet={tab}")
    with urllib.request.urlopen(url, timeout=30) as resp:
        content = resp.read().decode("utf-8")
    return list(csv.DictReader(content.splitlines()))


# ── DB cache load ─────────────────────────────────────────────────────────────

def load_db_cache(path):
    """Return dict: phone_number → {got_demo, is_onboarded}."""
    with open(path) as f:
        data = json.load(f)
    rows = data if isinstance(data, list) else data.get("rows", [])
    mapping = {}
    for r in rows:
        phone = normalize_phone(str(r.get("phone_number", "")))
        if phone:
            mapping[phone] = {
                "got_demo":     bool(r.get("got_demo", False)),
                "is_onboarded": bool(r.get("is_onboarded", False)),
            }
    return mapping


# ── Core computation ──────────────────────────────────────────────────────────

def build_funnel(sheet_rows, db_status, date_from, date_to):
    """
    Two-pass build:
      Pass 1: all rows → amb_cohort_first (for cohort classification)
      Pass 2: window rows only → accumulate metrics

    Returns (ambassadors list, data_quality dict).
    """
    today = datetime.now().date()

    # Pass 1: cohort classification (all-time first visit, excluding today+)
    amb_cohort_first = {}
    for row in sheet_rows:
        d = row_date(row)
        if not d or d >= today:
            continue
        name = ambassador_name(row)
        if name not in amb_cohort_first or d < amb_cohort_first[name]:
            amb_cohort_first[name] = d

    def cohort(name):
        if name in EP_REFERRED_OVERRIDE:
            return "New"
        first = amb_cohort_first.get(name)
        if first is None:
            return "Unknown"
        return "New" if first >= NEW_CUTOFF else "Old"

    # Pass 2: window-filtered accumulation
    amb_visits = defaultdict(list)
    amb_first  = {}
    amb_last   = {}

    for row in sheet_rows:
        d = row_date(row)
        if not d or d < date_from or d > date_to:
            continue
        name = ambassador_name(row)
        amb_visits[name].append(row)
        if name not in amb_first or d < amb_first[name]:
            amb_first[name] = d
        if name not in amb_last or d > amb_last[name]:
            amb_last[name] = d

    ambassadors = []
    for name, rows in sorted(amb_visits.items()):
        visits  = len(rows)
        openers = sum(1 for r in rows if opener_passed(r))

        phones_with_data = set()
        phones_all       = set()
        for r in rows:
            p = normalize_phone(r.get(COL_PHONE, ""))
            if p:
                phones_all.add(p)
                if p in db_status:
                    phones_with_data.add(p)

        if db_status:
            demos       = sum(1 for p in phones_all if db_status.get(p, {}).get("got_demo"))
            onboardings = sum(1 for p in phones_all if db_status.get(p, {}).get("is_onboarded"))
        else:
            demos       = sum(1 for r in rows if r.get("Golden Flow Amount", "").strip() not in ("", "0"))
            onboardings = sum(1 for r in rows if r.get("QR Setup Done", "").strip().lower() in ("yes","true","done","1"))

        first_d = amb_first.get(name)
        last_d  = amb_last.get(name, first_d)
        days_active = (last_d - first_d).days + 1 if first_d and last_d else 1

        ambassadors.append({
            "name":               name,
            "cohort":             cohort(name),
            "first_visit":        first_d,
            "last_visit":         last_d,
            "days_active":        days_active,
            "visits":             visits,
            "openers":            openers,
            "demos":              demos,
            "onboardings":        onboardings,
            "onboardings_per_day": round(onboardings / days_active, 1),
            "phones_all":         len(phones_all),
            "phones_db":          len(phones_with_data),
        })

    # Data quality
    total_rows    = sum(a["visits"]     for a in ambassadors)
    total_phones  = sum(a["phones_all"] for a in ambassadors)
    total_db_hit  = sum(a["phones_db"]  for a in ambassadors)

    data_quality = {
        "total_visits":   total_rows,
        "visits_w_phone": total_phones,
        "phone_coverage": total_phones / total_rows if total_rows else 0,
        "db_match_rate":  total_db_hit / total_phones if total_phones else 0,
        "db_mode":        bool(db_status),
    }

    return ambassadors, data_quality


def aggregate(rows):
    if not rows:
        return {"visits": 0, "openers": 0, "demos": 0, "onboardings": 0,
                "days_active": 1, "onboardings_per_day": 0.0}
    first_dates = [r["first_visit"] for r in rows if r.get("first_visit")]
    last_dates  = [r["last_visit"]  for r in rows if r.get("last_visit")]
    if first_dates and last_dates:
        days_active = (max(last_dates) - min(first_dates)).days + 1
    else:
        days_active = 1
    onboardings = sum(r["onboardings"] for r in rows)
    return {
        "visits":             sum(r["visits"]      for r in rows),
        "openers":            sum(r["openers"]     for r in rows),
        "demos":              sum(r["demos"]       for r in rows),
        "onboardings":        onboardings,
        "days_active":        days_active,
        "onboardings_per_day": round(onboardings / days_active, 1),
    }


def pct(num, den):
    if not den:
        return "—"
    return f"{round(num / den * 100)}%"


# ── HTML generation ───────────────────────────────────────────────────────────

CARD_CSS = """
  :root {
    --zar-gold: #B8992E;
    --zar-gold-light: #CBAF4A;
    --zar-gold-dark: #9A7E24;
    --background: #F5F0E8;
    --card: #FFFFFF;
    --border: #E8E3DB;
    --text: #1A1A1A;
    --text-secondary: #6B6B6B;
    --success: #16a34a;
    --danger: #dc2626;
    --warning: #f59e0b;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: var(--background);
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 30px;
    color: var(--text);
  }
  h1 {
    font-family: 'DM Sans', sans-serif;
    font-size: 1.8rem; font-weight: 700;
    margin-bottom: 6px;
  }
  .subtitle {
    font-size: 0.85rem;
    color: var(--text-secondary);
    margin-bottom: 30px;
  }
  .data-card {
    margin-top: 20px;
    background: var(--card);
    border-radius: 20px;
    padding: 1.5rem 2rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    border: 1px solid var(--border);
    width: 100%;
    max-width: 960px;
  }
  .data-card h2 {
    font-family: 'DM Sans', sans-serif;
    font-size: 1.1rem; font-weight: 600;
    margin-bottom: 1rem;
    display: flex; align-items: center; gap: 0.5rem;
  }
  .data-card h2 .num {
    background: linear-gradient(135deg, var(--zar-gold), var(--zar-gold-light));
    color: white;
    width: 26px; height: 26px;
    border-radius: 8px;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 0.8rem; font-weight: 600;
  }
  .stat-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 1rem;
    margin-bottom: 1.25rem;
  }
  .stat-grid-2 {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.75rem;
    margin-bottom: 1rem;
  }
  .stat-grid-5 {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 0.75rem;
    margin-bottom: 1rem;
  }
  .stat-box {
    background: var(--background);
    padding: 1rem;
    border-radius: 12px;
    text-align: center;
  }
  .stat-value {
    font-family: 'DM Sans', sans-serif;
    font-size: 1.8rem; font-weight: 700;
    color: var(--zar-gold-dark);
  }
  .stat-value-sm {
    font-family: 'DM Sans', sans-serif;
    font-size: 1.4rem; font-weight: 700;
    color: var(--zar-gold-dark);
  }
  .cohort-col .stat-value-sm {
    font-size: 1.1rem;
    white-space: nowrap;
    overflow: visible;
  }
  .stat-label {
    font-size: 0.8rem;
    color: var(--text-secondary);
    margin-top: 0.25rem;
  }
  .insight {
    background: linear-gradient(135deg, rgba(184,153,46,0.08), rgba(184,153,46,0.02));
    border-left: 3px solid var(--zar-gold);
    padding: 1rem;
    margin-top: 1rem;
    font-size: 0.85rem;
    border-radius: 0 12px 12px 0;
  }
  .insight strong { color: var(--zar-gold-dark); }
  .metric-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem 1.5rem;
    font-size: 0.78rem;
    color: var(--text-secondary);
    margin-bottom: 1rem;
  }
  .metric-legend span { white-space: nowrap; }
  .metric-legend strong { color: var(--text); font-weight: 600; }
  /* Hero comparison */
  .hero-comparison {
    background: var(--background);
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.25rem;
    text-align: center;
  }
  .hero-label {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-secondary);
    margin-bottom: 0.75rem;
  }
  .hero-cols {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 2rem;
  }
  .hero-col { text-align: center; }
  .hero-val {
    font-family: 'DM Sans', sans-serif;
    font-size: 2.2rem;
    font-weight: 700;
    line-height: 1.1;
  }
  .hero-winner .hero-val { color: var(--zar-gold-dark); }
  .hero-loser  .hero-val { color: #9CA3AF; }
  .hero-name {
    font-size: 0.78rem;
    color: var(--text-secondary);
    margin-top: 0.3rem;
  }
  .hero-vs {
    font-size: 0.9rem;
    color: var(--text-secondary);
    font-weight: 500;
  }
  /* Cohort columns */
  .cohort-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.25rem;
    margin-top: 0.5rem;
  }
  .cohort-col {
    background: var(--background);
    border-radius: 12px;
    padding: 1rem 1.25rem;
  }
  .cohort-col h3 {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.95rem; font-weight: 600;
    margin-bottom: 0.75rem;
    display: flex; align-items: center; gap: 0.4rem;
  }
  .dot-new { width: 10px; height: 10px; border-radius: 50%; background: #16a34a; display: inline-block; }
  .dot-old { width: 10px; height: 10px; border-radius: 50%; background: #dc2626; display: inline-block; }
  .conv-list { font-size: 0.82rem; color: var(--text-secondary); margin-top: 0.5rem; }
  .conv-list span { font-family: 'DM Sans', sans-serif; font-weight: 600; color: var(--text); }
  table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  th {
    padding: 0.6rem 0.75rem;
    text-align: left;
    color: var(--text-secondary);
    font-weight: 500; font-size: 0.75rem;
    text-transform: uppercase; letter-spacing: 0.05em;
    border-bottom: 2px solid var(--border);
  }
  th.num-col { text-align: right; }
  td {
    padding: 0.6rem 0.75rem;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }
  td.num-col { text-align: right; font-family: 'DM Sans', sans-serif; font-weight: 600; }
  tr:last-child td { border-bottom: none; }
  tr.total-row td {
    font-weight: 700;
    background: rgba(184,153,46,0.08);
    border-bottom: none;
  }
  .badge {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    border-radius: 100px;
    font-size: 0.7rem; font-weight: 600;
  }
  .badge-success { background: rgba(22,163,74,0.15); color: #16a34a; }
  .badge-warning { background: rgba(184,153,46,0.15); color: var(--zar-gold-dark); }
  .badge-danger  { background: rgba(220,38,38,0.15); color: #dc2626; }
  .badge-new { background: rgba(22,163,74,0.15); color: #16a34a;
               padding: 0.15rem 0.5rem; border-radius: 100px; font-size: 0.7rem; font-weight: 600; }
  .badge-old { background: rgba(220,38,38,0.15); color: #dc2626;
               padding: 0.15rem 0.5rem; border-radius: 100px; font-size: 0.7rem; font-weight: 600; }
  .badge-unk { background: rgba(107,107,107,0.15); color: var(--text-secondary);
               padding: 0.15rem 0.5rem; border-radius: 100px; font-size: 0.7rem; font-weight: 600; }
  .rate-bar {
    display: inline-block; height: 8px; border-radius: 4px; vertical-align: middle;
  }
  footer { margin-top: 30px; font-size: 0.75rem; color: var(--text-secondary); }
  @media (max-width: 640px) {
    .stat-grid { grid-template-columns: repeat(3, 1fr); }
    .cohort-grid { grid-template-columns: 1fr; }
    .stat-grid-2 { grid-template-columns: repeat(2, 1fr); }
    .stat-grid-5 { grid-template-columns: repeat(3, 1fr); }
  }
"""

FONTS_LINK = '<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">'


def _stat_box(value, label, sm=False):
    cls = "stat-value-sm" if sm else "stat-value"
    return (
        f'<div class="stat-box">'
        f'<div class="{cls}">{value}</div>'
        f'<div class="stat-label">{label}</div>'
        f'</div>'
    )


def cohort_section(label, totals, dot_class):
    v = totals["visits"]
    o = totals["openers"]
    d = totals["demos"]
    b = totals["onboardings"]
    bpd = totals["onboardings_per_day"]
    html = (
        f'<div class="cohort-col">'
        f'<h3><span class="{dot_class}"></span> {label}</h3>'
        f'<div class="stat-grid-2">'
        f'{_stat_box(f"{v:,}", "Visits", sm=True)}'
        f'{_stat_box(f"{d:,}", "Demos", sm=True)}'
        f'{_stat_box(f"{b:,}", "Onboardings", sm=True)}'
        f'{_stat_box(f"{bpd}/day", "B/day", sm=True)}'
        f'</div>'
        f'<div class="conv-list">'
        f'O/V <span>{pct(o, v)}</span> &nbsp;·&nbsp; '
        f'D/O <span>{pct(d, o)}</span> &nbsp;·&nbsp; '
        f'B/D <span>{pct(b, d)}</span> &nbsp;·&nbsp; '
        f'B/V <span>{pct(b, v)}</span>'
        f'</div>'
        f'</div>'
    )
    return html


def hero_comparison(new_totals, old_totals):
    new_bpd = new_totals["onboardings_per_day"]
    old_bpd = old_totals["onboardings_per_day"]

    # Determine winner
    new_wins = new_bpd >= old_bpd
    new_cls  = "hero-winner" if new_wins else "hero-loser"
    old_cls  = "hero-loser"  if new_wins else "hero-winner"

    # Multiplier
    if old_bpd > 0:
        mult = round(new_bpd / old_bpd)
        callout = f"EP-Referred contractors onboard at <strong>{mult}&times; the rate</strong>"
    elif new_bpd > 0:
        callout = "EP-Referred contractors are onboarding; Legacy has zero"
    else:
        callout = "No onboardings recorded in this window"

    html = (
        f'<div class="hero-comparison">'
        f'<div class="hero-label">Onboardings / Day</div>'
        f'<div class="hero-cols">'
        f'<div class="hero-col {new_cls}">'
        f'<div class="hero-val">{new_bpd}/day</div>'
        f'<div class="hero-name">EP-Referred</div>'
        f'</div>'
        f'<div class="hero-vs">vs</div>'
        f'<div class="hero-col {old_cls}">'
        f'<div class="hero-val">{old_bpd}/day</div>'
        f'<div class="hero-name">Legacy</div>'
        f'</div>'
        f'</div>'
        f'</div>'
        f'<div class="insight">{callout}</div>'
    )
    return html


def contractor_table(ambassadors):
    overall = aggregate(ambassadors)
    html = (
        '<div class="data-card">'
        '<h2><span class="num">3</span> Per-Contractor Breakdown</h2>'
        '<table>'
        '<thead><tr>'
        '<th>Contractor</th><th>Cohort</th>'
        '<th class="num-col">Visits</th><th class="num-col">Openers</th>'
        '<th class="num-col">Demos</th><th class="num-col">Onboardings</th>'
        '<th class="num-col">O/V</th><th class="num-col">D/O</th>'
        '<th class="num-col">B/D</th><th class="num-col">B/day</th>'
        '</tr></thead><tbody>'
    )
    for a in sorted(ambassadors, key=lambda x: (-x["visits"], x["name"])):
        badge_cls   = {"New": "badge-new", "Old": "badge-old"}.get(a["cohort"], "badge-unk")
        cohort_text = COHORT_LABEL.get(a["cohort"], a["cohort"])
        bpd = a["onboardings_per_day"]
        html += (
            f'<tr>'
            f'<td>{a["name"]}</td>'
            f'<td><span class="{badge_cls}">{cohort_text}</span></td>'
            f'<td class="num-col">{a["visits"]:,}</td>'
            f'<td class="num-col">{a["openers"]:,}</td>'
            f'<td class="num-col">{a["demos"]:,}</td>'
            f'<td class="num-col">{a["onboardings"]:,}</td>'
            f'<td class="num-col">{pct(a["openers"], a["visits"])}</td>'
            f'<td class="num-col">{pct(a["demos"], a["openers"])}</td>'
            f'<td class="num-col">{pct(a["onboardings"], a["demos"])}</td>'
            f'<td class="num-col">{bpd}/day</td>'
            f'</tr>'
        )
    ov = overall
    html += (
        f'<tr class="total-row">'
        f'<td>TOTAL</td><td></td>'
        f'<td class="num-col">{ov["visits"]:,}</td>'
        f'<td class="num-col">{ov["openers"]:,}</td>'
        f'<td class="num-col">{ov["demos"]:,}</td>'
        f'<td class="num-col">{ov["onboardings"]:,}</td>'
        f'<td class="num-col">{pct(ov["openers"], ov["visits"])}</td>'
        f'<td class="num-col">{pct(ov["demos"], ov["openers"])}</td>'
        f'<td class="num-col">{pct(ov["onboardings"], ov["demos"])}</td>'
        f'<td class="num-col">{ov["onboardings_per_day"]}/day</td>'
        f'</tr>'
    )
    html += '</tbody></table></div>'
    return html


def generate_html(ambassadors, date_from, date_to):
    run_date   = datetime.now().strftime("%Y-%m-%d %H:%M PKT")
    window_str = f"{date_from.strftime('%b %-d')} – {date_to.strftime('%b %-d')}"

    overall    = aggregate(ambassadors)
    new_ambs   = [a for a in ambassadors if a["cohort"] == "New"]
    old_ambs   = [a for a in ambassadors if a["cohort"] == "Old"]
    new_totals = aggregate(new_ambs)
    old_totals = aggregate(old_ambs)
    new_count  = len(new_ambs)
    old_count  = len(old_ambs)

    ov = overall
    overall_insight = (
        f'O/V <strong>{pct(ov["openers"], ov["visits"])}</strong> &nbsp;·&nbsp; '
        f'D/O <strong>{pct(ov["demos"], ov["openers"])}</strong> &nbsp;·&nbsp; '
        f'B/D <strong>{pct(ov["onboardings"], ov["demos"])}</strong> &nbsp;·&nbsp; '
        f'B/V <strong>{pct(ov["onboardings"], ov["visits"])}</strong>'
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EP-Referred vs Legacy Contractors — Funnel</title>
{FONTS_LINK}
<style>{CARD_CSS}</style>
</head>
<body>
<h1>EP-Referred vs Legacy Contractor Funnel</h1>
<div class="subtitle">
  {window_str} &nbsp;&middot;&nbsp;
  EP-Referred = first visit &ge; {NEW_CUTOFF} or override &nbsp;&middot;&nbsp;
  {new_count} EP-Referred &nbsp;&middot;&nbsp; {old_count} Legacy
</div>

<div class="data-card">
  <h2><span class="num">1</span> Overall Scorecard</h2>
  <div class="metric-legend">
    <span><strong>O/V</strong> &mdash; opener rate (% of visits where merchant engaged)</span>
    <span><strong>D/O</strong> &mdash; demo rate (% of openers who received a demo)</span>
    <span><strong>B/D</strong> &mdash; onboarding rate (% of demos that converted to onboarding)</span>
    <span><strong>B/V</strong> &mdash; overall yield (onboardings per visit)</span>
  </div>
  <div class="stat-grid">
    {_stat_box(f'{ov["visits"]:,}',      "Visits")}
    {_stat_box(f'{ov["openers"]:,}',     "Openers")}
    {_stat_box(f'{ov["demos"]:,}',       "Demos")}
    {_stat_box(f'{ov["onboardings"]:,}', "Onboardings")}
    {_stat_box(f'{ov["onboardings_per_day"]}/day', "Onboardings/day")}
  </div>
  <div class="insight">{overall_insight}</div>
</div>

<div class="data-card">
  <h2><span class="num">2</span> Cohort Comparison</h2>
  {hero_comparison(new_totals, old_totals)}
  <div class="cohort-grid">
    {cohort_section(f"EP-Referred Contractors ({new_count})", new_totals, "dot-new")}
    {cohort_section(f"Legacy Contractors ({old_count})", old_totals, "dot-old")}
  </div>
</div>

{contractor_table(ambassadors)}

<footer>Generated {run_date}</footer>
</body>
</html>"""
    return html


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    today          = date.today()
    yesterday      = today - timedelta(days=1)
    last_week_mon  = today - timedelta(days=today.weekday() + 7)

    parser = argparse.ArgumentParser()
    parser.add_argument("--json", metavar="PATH",
                        help="Path to DB cache JSON (from retargeting_status_query)")
    parser.add_argument("--from", dest="date_from", metavar="YYYY-MM-DD",
                        default=last_week_mon.isoformat(),
                        help=f"Window start date (default: {last_week_mon})")
    parser.add_argument("--to", dest="date_to", metavar="YYYY-MM-DD",
                        default=yesterday.isoformat(),
                        help=f"Window end date (default: {yesterday})")
    args = parser.parse_args()

    date_from = date.fromisoformat(args.date_from)
    date_to   = date.fromisoformat(args.date_to)
    window_str = f"{date_from.strftime('%b %-d')} – {date_to.strftime('%b %-d')}"

    print(f"Window: {window_str}  ({date_from} → {date_to})")
    print("Fetching sheet...")
    sheet_rows = fetch_rows()
    print(f"  {len(sheet_rows)} rows fetched")

    db_status = {}
    if args.json:
        print(f"Loading DB cache from {args.json}...")
        db_status = load_db_cache(args.json)
        print(f"  {len(db_status)} phones in DB cache")
    else:
        print("No --json flag — running in sheet-only mode (demo/onboarding from sheet columns)")

    ambassadors, data_quality = build_funnel(sheet_rows, db_status, date_from, date_to)

    print(f"\n{'Contractor':<22} {'Cohort':<12} {'V':>5} {'O':>5} {'D':>5} {'B':>5}  O/V   D/O   B/D  B/day")
    print("-" * 88)
    for a in sorted(ambassadors, key=lambda x: (-x["visits"], x["name"])):
        cohort_disp = COHORT_LABEL.get(a["cohort"], a["cohort"])
        print(f"{a['name']:<22} {cohort_disp:<12} {a['visits']:>5} {a['openers']:>5} "
              f"{a['demos']:>5} {a['onboardings']:>5}  "
              f"{pct(a['openers'],a['visits']):>5}  "
              f"{pct(a['demos'],a['openers']):>5}  "
              f"{pct(a['onboardings'],a['demos']):>5}  "
              f"{a['onboardings_per_day']}/day")

    overall = aggregate(ambassadors)
    print("-" * 88)
    print(f"{'TOTAL':<22} {'':12} {overall['visits']:>5} {overall['openers']:>5} "
          f"{overall['demos']:>5} {overall['onboardings']:>5}  "
          f"{pct(overall['openers'],overall['visits']):>5}  "
          f"{pct(overall['demos'],overall['openers']):>5}  "
          f"{pct(overall['onboardings'],overall['demos']):>5}  "
          f"{overall['onboardings_per_day']}/day")

    new_t = aggregate([a for a in ambassadors if a["cohort"] == "New"])
    old_t = aggregate([a for a in ambassadors if a["cohort"] == "Old"])
    print(f"\n{'EP-Referred':<22} {'EP-Referred':12} {new_t['visits']:>5} {new_t['openers']:>5} "
          f"{new_t['demos']:>5} {new_t['onboardings']:>5}  "
          f"{pct(new_t['openers'],new_t['visits']):>5}  "
          f"{pct(new_t['demos'],new_t['openers']):>5}  "
          f"{pct(new_t['onboardings'],new_t['demos']):>5}  "
          f"{new_t['onboardings_per_day']}/day")
    print(f"{'Legacy':<22} {'Legacy':12} {old_t['visits']:>5} {old_t['openers']:>5} "
          f"{old_t['demos']:>5} {old_t['onboardings']:>5}  "
          f"{pct(old_t['openers'],old_t['visits']):>5}  "
          f"{pct(old_t['demos'],old_t['openers']):>5}  "
          f"{pct(old_t['onboardings'],old_t['demos']):>5}  "
          f"{old_t['onboardings_per_day']}/day")

    print(f"\nPhone coverage: {round(data_quality['phone_coverage']*100)}%  "
          f"DB match rate: {round(data_quality['db_match_rate']*100)}%")

    out_name = f"ambassador_cohort_{today.strftime('%Y%m%d')}.html"
    html = generate_html(ambassadors, date_from, date_to)
    with open(out_name, "w") as f:
        f.write(html)
    print(f"\nHTML written → {out_name}")


if __name__ == "__main__":
    main()
