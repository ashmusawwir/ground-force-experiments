#!/usr/bin/env python3
"""Single entry point for the Ramadan Visit Timing experiment."""

import sys

from data import (
    fetch_rows, split_by_ramadan, split_by_window,
    detect_batch_logging, ambassador_city,
)
from funnel import (
    FunnelMetrics, PeriodInfo, ambassador_breakdown,
    bucket_breakdown, window_comparison, productivity_summary,
    hourly_heatmap, hourly_totals, fatigue_curve, weekly_trend,
    city_breakdown, sequential_credibility, credibility_estimate,
)
from output import (
    print_period_comparison, print_bucket_breakdown,
    print_window_comparison, print_hourly_heatmap,
    print_ambassador_summary, print_productivity,
    print_batch_logging_warnings, print_weekly_trend,
    print_ambassador_breakdown,
    print_sequential_monitor, print_credibility_estimate,
)
from flowchart import generate_html, write_html
from config import DEFAULT_CITY


def main():
    print("Fetching visit form data...", file=sys.stderr)
    rows = fetch_rows()
    if not rows:
        print("No data returned from sheet.", file=sys.stderr)
        sys.exit(1)

    # Split periods
    baseline, ramadan = split_by_ramadan(rows)
    base_info, ram_info = PeriodInfo(baseline), PeriodInfo(ramadan)
    base_m, ram_m = FunnelMetrics(baseline), FunnelMetrics(ramadan)

    # Terminal output
    print_period_comparison(base_m, ram_m, base_info, ram_info)

    if ramadan:
        # Window split (day / evening / night)
        day_rows, eve_rows, night_rows = split_by_window(ramadan)
        wc = window_comparison(day_rows, eve_rows, night_rows)
        print_window_comparison(wc)

        # Bucket breakdown
        ram_buckets = bucket_breakdown(ramadan, DEFAULT_CITY)
        pre_buckets = bucket_breakdown(baseline, DEFAULT_CITY)
        print_bucket_breakdown(ram_buckets, DEFAULT_CITY)

        # Hourly heatmap
        hmap = hourly_heatmap(ramadan)
        totals = hourly_totals(ramadan)
        print_hourly_heatmap(totals)

        # Ambassador summary
        prods = productivity_summary(ramadan)
        print_ambassador_summary(prods)
        print_ambassador_breakdown(ramadan, ram_info)

        # Productivity
        print_productivity(base_info, ram_info, base_m, ram_m)

        # Batch logging
        batch_flags = detect_batch_logging(ramadan)
        print_batch_logging_warnings(batch_flags)

        # Weekly trend
        weeks = weekly_trend(ramadan)
        print_weekly_trend(weeks)

        # Sequential credibility monitor
        trajectory = sequential_credibility(ramadan)
        est_days = credibility_estimate(trajectory)
        print_sequential_monitor(trajectory)
        print_credibility_estimate(est_days, trajectory)

        # City comparison
        city_metrics = city_breakdown(ramadan)

        # Ambassador funnel
        amb_funnel = ambassador_breakdown(ramadan)

        # Generate HTML
        html = generate_html(
            base_m=base_m, ram_m=ram_m,
            base_info=base_info, ram_info=ram_info,
            wc=wc,
            heatmap=hmap, totals=totals,
            ram_buckets=ram_buckets, pre_buckets=pre_buckets,
            city=DEFAULT_CITY,
            city_metrics=city_metrics,
            prods=prods, amb_funnel=amb_funnel,
            weeks=weeks,
            batch_flags=batch_flags,
            trajectory=trajectory,
            est_days=est_days,
        )
        write_html(html)
    else:
        print("  No Ramadan data yet — only pre-Ramadan baseline available.", file=sys.stderr)


if __name__ == "__main__":
    main()
