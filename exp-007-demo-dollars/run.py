#!/usr/bin/env python3
"""Single entry point for the Post-Demo Retargeting experiment."""

import argparse
import json
import re
import sys

from data import fetch_rows, get_experiment_rows, is_onboarding, set_db_status
from funnel import build_journeys, RetargetingMetrics, PeriodInfo, no_phone_count, phone_audit
from output import (
    print_data_quality, print_phone_audit, print_retargeting_funnel,
    print_conversion_comparison, print_tier_comparison,
    print_ambassador_breakdown, print_days_distribution, print_retarget_list,
)
from flowchart import write_html


def _load_db_status(path):
    """Load DB status JSON and populate the overlay keyed by normalized phone."""
    with open(path) as f:
        data = json.load(f)
    records = data.get("db_status", data) if isinstance(data, dict) else data
    mapping = {}
    for rec in records:
        phone = re.sub(r'\D', '', rec.get("phone_number") or "")
        if phone:
            mapping[phone] = {
                "got_demo": bool(rec.get("got_demo", False)),
                "is_onboarded": bool(rec.get("is_onboarded", False)),
                "first_demo_date": rec.get("first_demo_date"),
                "onboarding_date": rec.get("onboarding_date"),
                "demo_amount": rec.get("demo_amount"),
            }
    set_db_status(mapping)
    print(f"  DB overlay loaded: {len(mapping)} phones", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="EXP-007 Post-Demo Retargeting")
    parser.add_argument("--json", metavar="PATH", help="DB status cache JSON file")
    args = parser.parse_args()

    if args.json:
        _load_db_status(args.json)

    print("Fetching visit form data...", file=sys.stderr)
    rows = fetch_rows()
    if not rows:
        print("No data returned from sheet.", file=sys.stderr)
        sys.exit(1)

    exp_rows = get_experiment_rows(rows)
    info = PeriodInfo(exp_rows)

    onb_rows = [r for r in exp_rows if is_onboarding(r)]
    total_onb = len(onb_rows)
    no_phone = no_phone_count(exp_rows)

    print_data_quality(total_onb, no_phone, info)

    audit = phone_audit(exp_rows)
    print_phone_audit(audit)

    journeys = build_journeys(exp_rows)
    metrics = RetargetingMetrics(journeys)

    print_retargeting_funnel(metrics, journeys)
    print_conversion_comparison(metrics)
    print_tier_comparison(metrics)
    print_ambassador_breakdown(journeys)
    print_days_distribution(metrics)
    print_retarget_list(journeys)

    if exp_rows:
        write_html(metrics, journeys, info, total_onb, no_phone)


if __name__ == "__main__":
    main()
