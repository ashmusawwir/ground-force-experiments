"""Fetch Google Sheet data, parse timestamps, classify rows."""

import csv
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple

from config import (
    SHEET_ID, SHEET_TAB, EXPERIMENT_START,
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
        result += timedelta(hours=5)  # UTC → PKT
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


def question_text(row: Row) -> str:
    return row.get(COL_QUESTIONS_ASKED, "").strip()


def split_questions(row: Row) -> List[str]:
    """Split compound question cell into individual topic strings.

    '[opener] company info; [opener] withdrawals' → ['Company Info', 'Withdrawals']
    """
    raw = question_text(row)
    if not raw:
        return []
    parts = [p.strip() for p in raw.split(";")]
    cleaned = []
    for p in parts:
        # Strip [opener] or any [...] prefix
        if p.startswith("["):
            idx = p.find("]")
            if idx != -1:
                p = p[idx + 1:].strip()
        if p:
            cleaned.append(p.title())
    return cleaned


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


# --- Period splitting ---

def split_by_period(rows: List[Row]) -> Tuple[List[Row], List[Row]]:
    """Split rows into (baseline, experiment), excluding today."""
    today = datetime.now().date()
    baseline, experiment = [], []
    for row in rows:
        d = row_date(row)
        if d is None:
            continue
        if d < EXPERIMENT_START:
            baseline.append(row)
        elif d < today:
            experiment.append(row)
    return baseline, experiment
