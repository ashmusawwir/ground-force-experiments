"""All terminal printing — tables, insights, formatting helpers."""

from config import EXPERIMENT_NAME, BASELINE_Q_DEMO_RATE, MIN_VISITS_FOR_INSIGHT
from funnel import QDemoMetrics, TopicConversion, PeriodInfo, ambassador_q_demo
from data import Row
from typing import List, Optional


def _fmt(rate: Optional[float]) -> str:
    return f"{rate:.1f}%" if rate is not None else "\u2014"


def _fmt_delta(base_rate: Optional[float], expt_rate: Optional[float]) -> str:
    if base_rate is None or expt_rate is None:
        return "\u2014"
    d = expt_rate - base_rate
    sign = "+" if d >= 0 else ""
    return f"{sign}{d:.1f}pp"


def print_q_demo_comparison(pre_m: QDemoMetrics, post_m: QDemoMetrics,
                             pre_info: PeriodInfo, post_info: PeriodInfo) -> None:
    print()
    print(f"  {EXPERIMENT_NAME}")
    print(f"  Pre-training:  {pre_info.range_str} ({pre_info.num_days} days)")
    print(f"  Post-training: {post_info.range_str} ({post_info.num_days} day{'s' if post_info.num_days != 1 else ''})")
    print()
    print(f"| {'Metric':<24} | {'Pre':>8} | {'Post':>8} | {'Delta':>10} |")
    print(f"|{'-'*26}|{'-'*10}|{'-'*10}|{'-'*12}|")

    rows = [
        ("Visits", str(pre_m.visits), str(post_m.visits), ""),
        ("Opener Passed", str(pre_m.opener_passed), str(post_m.opener_passed), ""),
        ("Questions Asked", str(pre_m.questions_asked), str(post_m.questions_asked), ""),
        ("Converted to Demo", str(pre_m.converted_to_demo), str(post_m.converted_to_demo), ""),
        ("Q\u2192Demo Rate", _fmt(pre_m.q_demo_rate), _fmt(post_m.q_demo_rate),
         _fmt_delta(pre_m.q_demo_rate, post_m.q_demo_rate)),
    ]

    for label, pre_val, post_val, delta in rows:
        print(f"| {label:<24} | {pre_val:>8} | {post_val:>8} | {delta:>10} |")

    print()
    print("  Insights:")
    if pre_m.q_demo_rate is not None and post_m.q_demo_rate is not None:
        delta = post_m.q_demo_rate - pre_m.q_demo_rate
        direction = "up" if delta >= 0 else "down"
        sign = "+" if delta >= 0 else ""
        print(f"    \u2022 Q\u2192Demo: {pre_m.q_demo_rate:.1f}% \u2192 {post_m.q_demo_rate:.1f}% ({sign}{delta:.1f}pp) \u2014 {direction}")
    if post_m.q_demo_rate is not None:
        vs_baseline = post_m.q_demo_rate - BASELINE_Q_DEMO_RATE
        sign = "+" if vs_baseline >= 0 else ""
        print(f"    \u2022 vs EXP-001 baseline ({BASELINE_Q_DEMO_RATE:.0f}%): {sign}{vs_baseline:.1f}pp")
    print()


def print_topic_conversion(topics: TopicConversion, info: PeriodInfo) -> None:
    print()
    print(f"  Per-Topic Q\u2192Demo Conversion \u2014 {info.range_str}")
    print()
    print(f"| {'Topic':<24} | {'Asked':>6} | {'Demo':>5} | {'Conv %':>7} |")
    print(f"|{'-'*26}|{'-'*8}|{'-'*7}|{'-'*9}|")

    for topic, asked, demo, rate in topics.topics:
        print(f"| {topic:<24} | {asked:>6} | {demo:>5} | {_fmt(rate):>7} |")
    print()


def print_ambassador_q_demo(rows: List[Row], info: PeriodInfo) -> None:
    amb_data = ambassador_q_demo(rows)

    print()
    print(f"  Per-Ambassador Q\u2192Demo \u2014 {info.range_str}")
    print()
    _hdr = "Q\u2192Demo %"
    print(f"| {'Ambassador':<20} | {'Qs Asked':>8} | {'Demos':>6} | {_hdr:>10} |")
    print(f"|{'-'*22}|{'-'*10}|{'-'*8}|{'-'*12}|")

    for name, m in amb_data:
        if m.questions_asked == 0:
            continue
        print(f"| {name:<20} | {m.questions_asked:>8} | {m.converted_to_demo:>6} | {_fmt(m.q_demo_rate):>10} |")

    # Total
    total = QDemoMetrics([r for rows_list in [rows] for r in rows_list])
    print(f"| {'TOTAL':<20} | {total.questions_asked:>8} | {total.converted_to_demo:>6} | {_fmt(total.q_demo_rate):>10} |")
    print()

    # Insights
    print("  Insights:")
    qualified = [(n, m) for n, m in amb_data if m.questions_asked >= MIN_VISITS_FOR_INSIGHT]
    if qualified:
        best = max(qualified, key=lambda x: x[1].q_demo_rate or 0)
        worst = min(qualified, key=lambda x: x[1].q_demo_rate if x[1].q_demo_rate is not None else 999)
        print(f"    \u2022 Best Q\u2192Demo: {best[0]} ({_fmt(best[1].q_demo_rate)})")
        print(f"    \u2022 Worst Q\u2192Demo: {worst[0]} ({_fmt(worst[1].q_demo_rate)})")
    print()
