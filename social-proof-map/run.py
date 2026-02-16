#!/usr/bin/env python3
"""Single entry point for the Social Proof Map experiment tracker."""

import sys

from data import fetch_rows, split_by_group
from funnel import FunnelMetrics, PeriodInfo, FlowchartNodes, ambassador_breakdown
from output import print_funnel_comparison, print_ambassador_breakdown
from flowchart import write_html


def main():
    print("Fetching visit form data...", file=sys.stderr)
    rows = fetch_rows()
    if not rows:
        print("No data returned from sheet.", file=sys.stderr)
        sys.exit(1)

    others, sharoon = split_by_group(rows)
    all_window = others + sharoon
    period_info = PeriodInfo(all_window)
    others_m, sharoon_m = FunnelMetrics(others), FunnelMetrics(sharoon)

    print_funnel_comparison(others_m, sharoon_m, period_info)
    print_ambassador_breakdown(others, period_info)

    # HTML report
    amb_data = ambassador_breakdown(others)
    total_m = FunnelMetrics(others)
    others_nodes = FlowchartNodes(others)
    sharoon_nodes = FlowchartNodes(sharoon)
    write_html(others_m, sharoon_m, period_info, amb_data, total_m,
               others_nodes, sharoon_nodes)


if __name__ == "__main__":
    main()
