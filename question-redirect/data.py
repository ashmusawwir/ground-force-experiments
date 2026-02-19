"""Fetch Google Sheet data, parse timestamps, classify rows."""

import csv
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple

import re

from config import (
    SHEET_ID, SHEET_TAB, EXPERIMENT_START, TRAINING_START,
    COL_TIMESTAMP, COL_VISIT_TYPE, COL_OPENER_OUTCOME,
    COL_QUESTIONS_ASKED, COL_GOLDEN_FLOW, COL_QR_SETUP, COL_AMBASSADOR,
    COL_PHONE,
    SKIP_QUESTIONS, QR_YES_VALUES, AMBASSADOR_NAMES,
)

Row = Dict[str, str]

# --- DB overlay for demo/onboarding verification ---
_db_status: Dict[str, Dict] = {}


def _normalize_phone(raw: str) -> str:
    """Strip non-digit chars → '923XXXXXXXXX' (12 digits)."""
    return re.sub(r'\D', '', raw)


def phone_number(row: Row) -> str:
    """Extract and normalize phone from the sheet row."""
    return _normalize_phone(row.get(COL_PHONE, ""))


def set_db_status(mapping: Dict[str, Dict]) -> None:
    """Populate DB overlay keyed by normalized phone number."""
    global _db_status
    _db_status = mapping


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
    """Split compound question cell into individual topic strings."""
    raw = question_text(row)
    if not raw:
        return []
    parts = [p.strip() for p in raw.split(";")]
    cleaned = []
    for p in parts:
        if p.startswith("["):
            idx = p.find("]")
            if idx != -1:
                p = p[idx + 1:].strip()
        if p:
            cleaned.append(p.title())
    return cleaned


def did_demo(row: Row) -> bool:
    phone = phone_number(row)
    if _db_status and phone in _db_status:
        return _db_status[phone].get("got_demo", False)
    # Sheet fallback
    val = row.get(COL_GOLDEN_FLOW, "").strip()
    if not val or val.lower() in ("0", "", "no", "false"):
        return False
    try:
        return float(val.replace("$", "").replace(",", "")) > 0
    except (ValueError, AttributeError):
        return val.lower() in ("yes", "done", "true")


def did_onboard(row: Row) -> bool:
    phone = phone_number(row)
    if _db_status and phone in _db_status:
        return _db_status[phone].get("is_onboarded", False)
    # Sheet fallback
    return row.get(COL_QR_SETUP, "").strip().lower() in QR_YES_VALUES


def ambassador_name(row: Row) -> str:
    raw = row.get(COL_AMBASSADOR, "").strip() or "Unknown"
    return AMBASSADOR_NAMES.get(raw, raw)


# --- Period splitting ---

def split_by_training(rows: List[Row]) -> Tuple[List[Row], List[Row]]:
    """Split rows into (pre-training, post-training).

    Pre-training: EXPERIMENT_START <= date < TRAINING_START
    Post-training: TRAINING_START <= date < today
    """
    today = datetime.now().date()
    pre, post = [], []
    for row in rows:
        d = row_date(row)
        if d is None or d < EXPERIMENT_START or d >= today:
            continue
        if d < TRAINING_START:
            pre.append(row)
        else:
            post.append(row)
    return pre, post


def get_experiment_rows(rows: List[Row]) -> List[Row]:
    """Get all rows from EXPERIMENT_START onwards (excluding today)."""
    today = datetime.now().date()
    return [r for r in rows if (d := row_date(r)) and EXPERIMENT_START <= d < today]
