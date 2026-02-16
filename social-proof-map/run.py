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

    control, treatment = split_by_group(rows)
    all_window = control + treatment
    period_info = PeriodInfo(all_window)
    control_m, treatment_m = FunnelMetrics(control), FunnelMetrics(treatment)

    # Terminal output
    print_funnel_comparison(control_m, treatment_m, period_info)
    print_ambassador_breakdown(treatment, period_info, group_label="Map Group")
    print_ambassador_breakdown(control, period_info, group_label="Control (no map)")

    # HTML report
    ctrl_amb = ambassador_breakdown(control)
    ctrl_total = FunnelMetrics(control)
    treat_amb = ambassador_breakdown(treatment)
    treat_total = FunnelMetrics(treatment)
    ctrl_nodes = FlowchartNodes(control)
    treat_nodes = FlowchartNodes(treatment)
    write_html(control_m, treatment_m, period_info,
               ctrl_amb, ctrl_total, treat_amb, treat_total,
               ctrl_nodes, treat_nodes)


if __name__ == "__main__":
    main()
