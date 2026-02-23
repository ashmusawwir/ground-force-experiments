#!/usr/bin/env python3
"""Single entry point for the Show Don't Tell experiment tracker."""

import sys

from data import fetch_rows, split_by_period
from funnel import FunnelMetrics, PeriodInfo, FlowchartNodes, ambassador_breakdown, QuestionDropoffData, DayOnDayProgression
from output import print_funnel_comparison, print_ambassador_breakdown
from flowchart import write_flowchart


def main():
    print("Fetching new form data...", file=sys.stderr)
    rows = fetch_rows()
    if not rows:
        print("No data returned from new form sheet.", file=sys.stderr)
        sys.exit(1)

    baseline, experiment = split_by_period(rows)
    base_info, expt_info = PeriodInfo(baseline), PeriodInfo(experiment)
    base_m, expt_m = FunnelMetrics(baseline), FunnelMetrics(experiment)

    print_funnel_comparison(base_m, expt_m, base_info, expt_info)
    print_ambassador_breakdown(experiment, expt_info)

    if experiment:
        amb_data = ambassador_breakdown(experiment)
        total_m = FunnelMetrics(experiment)
        dropoff = QuestionDropoffData(experiment)
        progression = DayOnDayProgression(experiment)
        write_flowchart(FlowchartNodes(experiment), expt_info,
                        base_m, expt_m, base_info, expt_info,
                        amb_data, total_m, dropoff, progression)


if __name__ == "__main__":
    main()
