"""Fetch Google Sheet data, parse timestamps, classify rows."""

import csv
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple

from config import (
    SHEET_ID, SHEET_TAB, EXPERIMENT_WINDOW_START,
    MAP_AMBASSADORS,
    COL_TIMESTAMP, COL_VISIT_TYPE, COL_OPENER_OUTCOME,
    COL_QUESTIONS_ASKED, COL_GOLDEN_FLOW, COL_QR_SETUP, COL_AMBASSADOR,
    SKIP_QUESTIONS, QR_YES_VALUES, AMBASSADOR_NAMES,
)

Row = Dict[str, str]


def fetch_rows() -> List[Row]:
    """Fetch all rows from the visit form sheet."""
    tab = urllib.parse.quote(SHEET_TAB)
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={tab}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        content = resp.read().decode("utf-8")
    return list(csv.DictReader(content.splitlines()))


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


# --- Row classifiers ---

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


# --- Group splitting (person-based with staggered start dates) ---

def split_by_group(rows: List[Row]) -> Tuple[List[Row], List[Row]]:
    """Split into (control, treatment) accounting for staggered map start dates.

    Treatment: ambassador is in MAP_AMBASSADORS AND row date >= their start date.
    Control:   ambassador NOT in MAP_AMBASSADORS (any date in window),
               OR ambassador in MAP_AMBASSADORS but date < their start (own baseline).
    Excludes today (incomplete day).
    """
    today = datetime.now().date()
    control, treatment = [], []
    for row in rows:
        d = row_date(row)
        if d is None or d < EXPERIMENT_WINDOW_START or d >= today:
            continue
        amb = ambassador_name(row)
        start = MAP_AMBASSADORS.get(amb)
        if start is not None and d >= start:
            treatment.append(row)
        else:
            control.append(row)
    return control, treatment
