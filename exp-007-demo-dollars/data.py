"""Fetch Google Sheet data, parse timestamps, classify rows."""

import csv
import urllib.request
import urllib.parse
import re
from datetime import datetime, timedelta, date

from config import (
    SHEET_ID, SHEET_TAB, EXPERIMENT_START,
    COL_TIMESTAMP, COL_VISIT_TYPE, COL_GOLDEN_FLOW, COL_QR_SETUP,
    COL_AMBASSADOR, COL_PHONE, COL_OPENER_OUTCOME,
    COL_SHOP_NAME, COL_LAT, COL_LNG,
    QR_YES_VALUES, AMBASSADOR_NAMES,
)

# --- DB overlay for demo/onboarding verification ---
_db_status = {}


def _normalize_phone(raw):
    """Strip non-digit chars -> '923XXXXXXXXX' (12 digits)."""
    return re.sub(r'\D', '', raw)


def phone_number(row):
    """Extract and normalize phone from the sheet row."""
    return _normalize_phone(row.get(COL_PHONE, ""))


def set_db_status(mapping):
    """Populate DB overlay keyed by normalized phone number."""
    global _db_status
    _db_status = mapping


def fetch_rows():
    """Fetch all rows from the visit form sheet."""
    tab = urllib.parse.quote(SHEET_TAB)
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={tab}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        content = resp.read().decode("utf-8")
    return list(csv.DictReader(content.splitlines()))


def parse_timestamp(ts):
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
        result += timedelta(hours=5)  # UTC -> PKT
    return result


def row_date(row):
    """Extract date from a row's timestamp."""
    ts = parse_timestamp(row.get(COL_TIMESTAMP, ""))
    return ts.date() if ts else None


def is_onboarding(row):
    vt = row.get(COL_VISIT_TYPE, "").strip().lower()
    return vt in ("onboarding", "new merchant", "new", "new onboarding")


def opener_passed(row):
    return row.get(COL_OPENER_OUTCOME, "").strip().lower() != "not interested"


def did_demo(row):
    """DB mode: look up phone in _db_status. No-DB fallback: sheet column."""
    phone = phone_number(row)
    if _db_status:
        if phone in _db_status:
            return _db_status[phone].get("got_demo", False)
        return False
    # Sheet fallback
    val = row.get(COL_GOLDEN_FLOW, "").strip()
    if not val or val.lower() in ("0", "", "no", "false"):
        return False
    try:
        return float(val.replace("$", "").replace(",", "")) > 0
    except (ValueError, AttributeError):
        return val.lower() in ("yes", "done", "true")


def did_onboard(row):
    """DB mode: look up phone in _db_status. No-DB fallback: sheet column."""
    phone = phone_number(row)
    if _db_status:
        if phone in _db_status:
            return _db_status[phone].get("is_onboarded", False)
        return False
    # Sheet fallback
    return row.get(COL_QR_SETUP, "").strip().lower() in QR_YES_VALUES


def db_demo_date(row):
    """Return first_demo_date from DB overlay, or None."""
    phone = phone_number(row)
    if _db_status and phone in _db_status:
        d = _db_status[phone].get("first_demo_date")
        if isinstance(d, str) and d:
            return date.fromisoformat(d)
        if isinstance(d, date):
            return d
    return None


def db_onboard_date(row):
    """Return onboarding_date from DB overlay, or None."""
    phone = phone_number(row)
    if _db_status and phone in _db_status:
        d = _db_status[phone].get("onboarding_date")
        if isinstance(d, str) and d:
            return date.fromisoformat(d)
        if isinstance(d, date):
            return d
    return None


def db_demo_amount(row):
    """Total demo note amount (atomic USDC) from DB overlay, or None."""
    phone = phone_number(row)
    if _db_status and phone in _db_status:
        return _db_status[phone].get("demo_amount")
    return None


def shop_name(row):
    return row.get(COL_SHOP_NAME, "").strip()


def location_lat(row):
    return row.get(COL_LAT, "").strip()


def location_lng(row):
    return row.get(COL_LNG, "").strip()


def ambassador_name(row):
    raw = row.get(COL_AMBASSADOR, "").strip() or "Unknown"
    return AMBASSADOR_NAMES.get(raw, raw)


def get_experiment_rows(rows):
    """Get all rows from EXPERIMENT_START onwards (excluding today)."""
    today = datetime.now().date()
    return [r for r in rows if (d := row_date(r)) and EXPERIMENT_START <= d < today]
