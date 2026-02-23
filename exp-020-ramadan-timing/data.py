"""Fetch Google Sheet data, parse timestamps, classify rows, time bucketing."""

import csv
import urllib.request
import urllib.parse
from collections import defaultdict
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple

from config import (
    SHEET_ID, SHEET_TAB, TAGGING_TAB, EXPERIMENT_START, RAMADAN_START,
    COL_TIMESTAMP, COL_VISIT_TYPE, COL_OPENER_OUTCOME,
    COL_QUESTIONS_ASKED, COL_GOLDEN_FLOW, COL_QR_SETUP, COL_AMBASSADOR,
    SKIP_QUESTIONS, QR_YES_VALUES, AMBASSADOR_NAMES, DEFAULT_CITY,
    CITY_TIMES, CITY_BUCKETS, BATCH_WINDOW_MINUTES, BATCH_MIN_VISITS,
)

Row = Dict[str, str]


# ── Sheet fetching ─────────────────────────────────────────────────

def _fetch_tab(tab: str) -> List[Row]:
    """Fetch a single tab from the Google Sheet."""
    encoded = urllib.parse.quote(tab)
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={encoded}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        content = resp.read().decode("utf-8")
    return list(csv.DictReader(content.splitlines()))


def fetch_rows() -> List[Row]:
    """Fetch all rows from the visit form sheet."""
    return _fetch_tab(SHEET_TAB)


def fetch_tagging() -> Dict[str, str]:
    """Fetch 'tagging' tab and build {ambassador_display_name: city} mapping."""
    rows = _fetch_tab(TAGGING_TAB)
    mapping = {}
    for row in rows:
        # Try common column names
        name_raw = (row.get("Ambassador Name", "") or row.get("Name", "")
                    or row.get("ambassador", "")).strip()
        city = (row.get("City", "") or row.get("city", "")).strip()
        if name_raw and city:
            # Resolve through AMBASSADOR_NAMES mapping
            display = AMBASSADOR_NAMES.get(name_raw, name_raw)
            mapping[display] = city
    return mapping


# ── Timestamp parsing ──────────────────────────────────────────────

def parse_timestamp(ts: str) -> Optional[datetime]:
    """Parse sheet timestamp string to datetime in PKT (UTC+5)."""
    if not ts:
        return None
    ts = ts.strip()
    result = None

    # ISO format: 2026-01-29T11:22:25.088Z
    if "T" in ts:
        try:
            clean = ts.split(".")[0].replace("Z", "")
            result = datetime.strptime(clean, "%Y-%m-%dT%H:%M:%S")
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
        result += timedelta(hours=5)  # UTC -> PKT
    return result


def row_date(row: Row) -> Optional[date]:
    """Extract date from a row's timestamp."""
    ts = parse_timestamp(row.get(COL_TIMESTAMP, ""))
    return ts.date() if ts else None


def row_hour(row: Row) -> Optional[int]:
    """Extract hour (PKT, 0-23) from visit timestamp."""
    ts = parse_timestamp(row.get(COL_TIMESTAMP, ""))
    return ts.hour if ts else None


def row_hour_float(row: Row) -> Optional[float]:
    """Hour as float (14.5 = 2:30pm) for granular bucketing."""
    ts = parse_timestamp(row.get(COL_TIMESTAMP, ""))
    if ts is None:
        return None
    return ts.hour + ts.minute / 60.0


def row_datetime(row: Row) -> Optional[datetime]:
    """Full datetime (PKT) for gap calculations."""
    return parse_timestamp(row.get(COL_TIMESTAMP, ""))


# ── Row classifiers ────────────────────────────────────────────────

def is_onboarding(row: Row) -> bool:
    vt = row.get(COL_VISIT_TYPE, "").strip().lower()
    return vt in ("onboarding", "new merchant", "new", "new onboarding")


def opener_passed(row: Row) -> bool:
    return row.get(COL_OPENER_OUTCOME, "").strip().lower() != "not interested"


def has_question(row: Row) -> bool:
    q = row.get(COL_QUESTIONS_ASKED, "").strip()
    return q.lower() not in SKIP_QUESTIONS


def did_demo(row: Row) -> bool:
    val = row.get(COL_GOLDEN_FLOW, "").strip()
    if not val or val.lower() in ("0", "", "no", "false"):
        return False
    try:
        return float(val.replace("$", "").replace(",", "")) > 0
    except (ValueError, AttributeError):
        return val.lower() in ("yes", "done", "true")


def did_onboard(row: Row) -> bool:
    return row.get(COL_QR_SETUP, "").strip().lower() in QR_YES_VALUES


def ambassador_name(row: Row) -> str:
    raw = row.get(COL_AMBASSADOR, "").strip() or "Unknown"
    return AMBASSADOR_NAMES.get(raw, raw)


# ── City mapping ───────────────────────────────────────────────────

_tagging_cache: Optional[Dict[str, str]] = None


def _get_tagging() -> Dict[str, str]:
    global _tagging_cache
    if _tagging_cache is None:
        try:
            _tagging_cache = fetch_tagging()
        except Exception:
            _tagging_cache = {}
    return _tagging_cache


def ambassador_city(row: Row) -> str:
    """Look up city from ambassador name via tagging tab."""
    name = ambassador_name(row)
    mapping = _get_tagging()
    return mapping.get(name, DEFAULT_CITY)


# ── Time bucketing ─────────────────────────────────────────────────

def time_bucket(hour_float: float, city: str = "Karachi") -> str:
    """Classify hour into a named time bucket for the given city."""
    buckets = CITY_BUCKETS.get(city, CITY_BUCKETS["Karachi"])
    for name, start, end in buckets:
        if start <= hour_float < end:
            return name
    # Handle edge: hour >= 24 (next day early morning) or < 9
    if hour_float < 9.0:
        return "Post-Taraweeh"  # late-night carryover
    return "Unknown"


def time_window(hour_float: float, city: str = "Karachi") -> str:
    """Classify into Daytime / Evening Transition / Nighttime."""
    times = CITY_TIMES.get(city, CITY_TIMES["Karachi"])
    if hour_float < times["iftar"]:
        return "Daytime"
    elif hour_float >= times["taraweeh_end"]:
        return "Nighttime"
    else:
        return "Evening Transition"


# ── Period splitting ───────────────────────────────────────────────

def split_by_ramadan(rows: List[Row]) -> Tuple[List[Row], List[Row]]:
    """Split into (pre-Ramadan baseline, Ramadan period), excluding today."""
    today = datetime.now().date()
    baseline, ramadan = [], []
    for row in rows:
        d = row_date(row)
        if d is None or d >= today:
            continue
        if d < RAMADAN_START:
            baseline.append(row)
        else:
            ramadan.append(row)
    return baseline, ramadan


def split_by_window(rows: List[Row]) -> Tuple[List[Row], List[Row], List[Row]]:
    """Split into (daytime, evening_transition, nighttime). City-aware."""
    daytime, evening, nighttime = [], [], []
    for row in rows:
        hf = row_hour_float(row)
        if hf is None:
            continue
        city = ambassador_city(row)
        w = time_window(hf, city)
        if w == "Daytime":
            daytime.append(row)
        elif w == "Nighttime":
            nighttime.append(row)
        else:
            evening.append(row)
    return daytime, evening, nighttime


# ── Batch-logging detection ────────────────────────────────────────

def detect_batch_logging(rows: List[Row]) -> List[dict]:
    """Flag clusters of 3+ visits within BATCH_WINDOW_MINUTES per ambassador per day.

    Returns list of {ambassador, date, count, timestamps} dicts.
    """
    # Group by (ambassador, date)
    groups: Dict[Tuple[str, date], List[datetime]] = defaultdict(list)
    for row in rows:
        dt = row_datetime(row)
        if dt is None:
            continue
        name = ambassador_name(row)
        d = dt.date()
        groups[(name, d)].append(dt)

    flags = []
    for (name, d), timestamps in groups.items():
        timestamps.sort()
        if len(timestamps) < BATCH_MIN_VISITS:
            continue
        # Sliding window: find clusters within BATCH_WINDOW_MINUTES
        i = 0
        while i < len(timestamps):
            cluster = [timestamps[i]]
            j = i + 1
            while j < len(timestamps):
                gap = (timestamps[j] - cluster[0]).total_seconds() / 60
                if gap <= BATCH_WINDOW_MINUTES:
                    cluster.append(timestamps[j])
                    j += 1
                else:
                    break
            if len(cluster) >= BATCH_MIN_VISITS:
                flags.append({
                    "ambassador": name,
                    "date": d,
                    "count": len(cluster),
                    "timestamps": [t.strftime("%H:%M") for t in cluster],
                })
                i = j  # skip past this cluster
            else:
                i += 1

    flags.sort(key=lambda f: (f["ambassador"], f["date"]))
    return flags
