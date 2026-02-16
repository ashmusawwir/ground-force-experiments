#!/usr/bin/env python3
"""Single entry point for the Question Redirect Protocol experiment tracker."""

import sys

from data import fetch_rows, split_by_training, get_experiment_rows
from funnel import QDemoMetrics, TopicConversion, PeriodInfo
from output import print_q_demo_comparison, print_topic_conversion, print_ambassador_q_demo
from flowchart import write_html


def main():
    print("Fetching visit form data...", file=sys.stderr)
    rows = fetch_rows()
    if not rows:
        print("No data returned from sheet.", file=sys.stderr)
        sys.exit(1)

    pre, post = split_by_training(rows)
    all_exp = get_experiment_rows(rows)

    pre_info, post_info = PeriodInfo(pre), PeriodInfo(post)
    all_info = PeriodInfo(all_exp)
    pre_m, post_m = QDemoMetrics(pre), QDemoMetrics(post)
    topics = TopicConversion(all_exp)

    print_q_demo_comparison(pre_m, post_m, pre_info, post_info)
    print_topic_conversion(topics, all_info)
    print_ambassador_q_demo(all_exp, all_info)

    if all_exp:
        write_html(pre_m, post_m, pre_info, post_info, topics, all_exp, all_info)


if __name__ == "__main__":
    main()
