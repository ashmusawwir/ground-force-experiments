#!/usr/bin/env python3
"""
Demo Dollars Usage Analysis — standalone one-pager.

Reads demo dollars data from a cache JSON (produced via Rube MCP workflow)
and assembles a self-contained HTML report.

Usage:
    python3 run.py --json /path/to/demo_dollars_cache.json
"""

import argparse
import csv
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path

# ── Visits sheet enrichment ────────────────────────────────────────

VISITS_SHEET_ID = "1bFf0NAQFFXIYYxMC1yJeqowRz6MwT_-xawZeg5H9wUQ"
SHOP_NAME_COL = 12   # 0-indexed: column M (Shop Name)
MERCHANT_PHONE_COL = 14  # 0-indexed: column O (Merchant Phone)
LAT_COL = 4          # 0-indexed: column E (Location Lat)
LNG_COL = 5          # 0-indexed: column F (Location Lng)


def normalize_phone(phone):
    """Strip non-digits, return 12-digit PK number or None."""
    if not phone:
        return None
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 12 and digits.startswith('92'):
        return digits
    return None


def _fetch_sheet_csv():
    """Fetch raw CSV text from visits sheet. Returns text or None on error."""
    url = f"https://docs.google.com/spreadsheets/d/{VISITS_SHEET_ID}/export?format=csv"
    try:
        resp = urllib.request.urlopen(url, timeout=15)
        return resp.read().decode('utf-8')
    except Exception as e:
        print(f"  Warning: could not fetch visits sheet: {e}", file=sys.stderr)
        return None


def fetch_sheet_business_names():
    """Fetch phone→business_name mapping from visits sheet.

    Returns dict mapping normalized phone (923...) to shop name.
    """
    text = _fetch_sheet_csv()
    if text is None:
        return {}

    mapping = {}
    reader = csv.reader(StringIO(text))
    next(reader, None)  # skip header
    for row in reader:
        if len(row) <= max(SHOP_NAME_COL, MERCHANT_PHONE_COL):
            continue
        shop = (row[SHOP_NAME_COL] or '').strip()
        phone = normalize_phone(row[MERCHANT_PHONE_COL])
        if shop and phone:
            mapping[phone] = shop
    return mapping


def fetch_sheet_locations():
    """Fetch phone→(lat, lng) mapping from visits sheet.

    Returns dict mapping normalized phone (923...) to {"lat": float, "lng": float}.
    Uses last occurrence per phone (most recent visit).
    """
    text = _fetch_sheet_csv()
    if text is None:
        return {}

    mapping = {}
    reader = csv.reader(StringIO(text))
    next(reader, None)  # skip header
    for row in reader:
        if len(row) <= max(LAT_COL, LNG_COL, MERCHANT_PHONE_COL):
            continue
        phone = normalize_phone(row[MERCHANT_PHONE_COL])
        lat_str = (row[LAT_COL] or '').strip()
        lng_str = (row[LNG_COL] or '').strip()
        if phone and lat_str and lng_str:
            try:
                mapping[phone] = {"lat": float(lat_str), "lng": float(lng_str)}
            except ValueError:
                pass
    return mapping


def enrich_business_names(recipients, quiet=False):
    """Enrich null business_name rows from visits sheet. Returns count enriched."""
    need = [r for r in recipients if not r.get('business_name')]
    if not need:
        return 0
    sheet_map = fetch_sheet_business_names()
    if not sheet_map:
        return 0
    enriched = 0
    for r in need:
        norm = normalize_phone(r.get('recipient_phone'))
        if norm and norm in sheet_map:
            r['business_name'] = sheet_map[norm]
            enriched += 1
    if not quiet and enriched:
        print(f"  Enriched {enriched} business names from visits sheet")
    return enriched


def enrich_location(recipients, quiet=False):
    """Enrich location_lat/location_lng from visits sheet. Returns count enriched."""
    need = [r for r in recipients if r.get('location_lat') is None]
    if not need:
        return 0
    loc_map = fetch_sheet_locations()
    if not loc_map:
        return 0
    enriched = 0
    for r in need:
        norm = normalize_phone(r.get('recipient_phone'))
        if norm and norm in loc_map:
            r['location_lat'] = loc_map[norm]['lat']
            r['location_lng'] = loc_map[norm]['lng']
            enriched += 1
    if not quiet and enriched:
        print(f"  Enriched {enriched} locations from visits sheet")
    return enriched


def main():
    parser = argparse.ArgumentParser(description="Demo Dollars Usage Analysis")
    parser.add_argument("--json", required=True, help="Path to demo_dollars_cache.json")
    parser.add_argument("--html", default="demo_dollars_usage.html", help="Output filename")
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args()

    cache = json.loads(Path(args.json).read_text())

    data = {
        "recipient_overview": cache.get("recipient_overview", []),
        "note_distribution": cache.get("note_distribution", []),
        "recipient_activity": cache.get("recipient_activity", []),
        "ambassador_summary": cache.get("ambassador_summary", []),
        "app_opens": cache.get("app_opens", []),
        "recipient_timing": cache.get("recipient_timing", []),
        "app_opens_detailed": cache.get("app_opens_detailed", []),
        "merchant_transactions": cache.get("merchant_transactions", []),
        "time_to_first_tx": cache.get("time_to_first_tx", []),
        "all_activity_timestamps": cache.get("all_activity_timestamps", []),
    }

    counts = (
        f"{len(data['recipient_overview'])} recipients, "
        f"{len(data['ambassador_summary'])} ambassadors, "
        f"{len(data['recipient_activity'])} activity rows"
    )

    if not data["recipient_overview"]:
        print("Error: no recipient data in cache JSON", file=sys.stderr)
        sys.exit(1)

    enrich_business_names(data["recipient_overview"], quiet=args.quiet)
    enrich_location(data["recipient_overview"], quiet=args.quiet)

    now_pkt = datetime.utcnow() + timedelta(hours=5)
    generated_at = now_pkt.strftime("%b %d, %Y %I:%M %p")

    base = Path(__file__).parent / "ui"
    shell = (base / "shell.html").read_text()
    css = (base / "style.css").read_text()
    js = (base / "app.js").read_text()
    blob = json.dumps(data, separators=(",", ":"))

    html = (shell
        .replace("/* __CSS__ */", css)
        .replace("// __DATA__", f"const RAW = {blob};")
        .replace("// __APP__", js)
        .replace("__GENERATED_AT__", generated_at))

    out_path = Path(__file__).resolve().parent / args.html
    out_path.write_text(html, encoding="utf-8")

    if not args.quiet:
        print(f"Generated {out_path}")
        print(f"  {counts}")


if __name__ == "__main__":
    main()
