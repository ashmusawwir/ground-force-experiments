#!/usr/bin/env python3
"""
Network Growth Through Merchants — standalone one-pager.

Reads merchant data from a cache JSON (produced by the main dashboard's
Rube MCP workflow) and assembles a self-contained HTML report.

Supports two cache shapes:
  - New granular: merchant_static + user_onboardings + user_activations
    + merchant_daily_activity + merchant_retention
  - Legacy: merchant_summary + merchant_retention

Usage:
    python3 run.py --json /path/to/systematic_cache.json
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Network Growth Through Merchants")
    parser.add_argument("--json", required=True, help="Path to systematic_cache.json")
    parser.add_argument("--html", default="network_growth_through_merchants.html", help="Output filename")
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args()

    cache = json.loads(Path(args.json).read_text())

    # New granular data shape
    if "merchant_static" in cache:
        data = {
            "merchant_static": cache.get("merchant_static", []),
            "user_onboardings": cache.get("user_onboardings", []),
            "user_activations": cache.get("user_activations", []),
            "user_txn_breakdown": cache.get("user_txn_breakdown", []),
            "merchant_daily_activity": cache.get("merchant_daily_activity", []),
            "merchant_retention": cache.get("merchant_retention", []),
            "user_invitations": cache.get("user_invitations", []),
            "user_first_transactions": cache.get("user_first_transactions", []),
            "user_cycling": cache.get("user_cycling", []),
            "rapid_onboarding": cache.get("rapid_onboarding", []),
            "cycling_timing": cache.get("cycling_timing", []),
            "merchant_fraud_summary": cache.get("merchant_fraud_summary", []),
        }
        count_label = f"{len(data['merchant_static'])} merchants, {len(data['user_onboardings'])} onboardings, {len(data['user_txn_breakdown'])} txn breakdowns, {len(data['merchant_retention'])} retention pairs"
    else:
        # Legacy: pre-aggregated merchant_summary
        data = {
            "merchant_summary": cache.get("merchant_summary", []),
            "merchant_retention": cache.get("merchant_retention", []),
        }
        if not data["merchant_summary"]:
            print("Error: no merchant data in cache JSON", file=sys.stderr)
            sys.exit(1)
        count_label = f"{len(data['merchant_summary'])} merchants, {len(data['merchant_retention'])} retention pairs"

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
        print(f"  {count_label}")


if __name__ == "__main__":
    main()
