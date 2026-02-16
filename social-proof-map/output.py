"""All terminal printing — tables, insights, formatting helpers."""

from config import EXPERIMENT_NAME, FUNNEL_STEPS, MIN_VISITS_FOR_INSIGHT
from funnel import FunnelMetrics, PeriodInfo, ambassador_breakdown
from data import Row
from typing import List, Optional


def _conv_rate(count: int, total: int) -> Optional[float]:
    return count / total * 100 if total else None


def _fmt_conv(rate: Optional[float]) -> str:
    return f"{rate:.1f}%" if rate is not None else "\u2014"


def _fmt_delta(base_rate: Optional[float], expt_rate: Optional[float]) -> str:
    if base_rate is None or expt_rate is None:
        return "\u2014"
    d = expt_rate - base_rate
    sign = "+" if d >= 0 else ""
    return f"{sign}{d:.1f}"


def print_funnel_comparison(others_m: FunnelMetrics, sharoon_m: FunnelMetrics,
                            period_info: PeriodInfo) -> None:
    others_d, sharoon_d = others_m.as_dict(), sharoon_m.as_dict()
    others_conv, sharoon_conv = others_m.step_conversions(), sharoon_m.step_conversions()

    print()
    print(f"  {EXPERIMENT_NAME} Experiment")
    print(f"  Window: {period_info.range_str} ({period_info.num_days} day{'s' if period_info.num_days != 1 else ''})")
    print(f"  Split: Sharoon (map) vs Others (no map)")
    print()
    _delta = "\u0394"
    print(f"| {'Step':<14} | {'Others #':>8} | {'Others Conv':>11} | {'Sharoon #':>9} | {'Sharoon Conv':>12} | {_delta:>6} |")
    print(f"|{'-'*16}|{'-'*10}|{'-'*13}|{'-'*11}|{'-'*14}|{'-'*8}|")

    for step in FUNNEL_STEPS:
        o_count = others_d[step]
        s_count = sharoon_d[step]
        o_conv = _fmt_conv(others_conv[step])
        s_conv = _fmt_conv(sharoon_conv[step])
        delta = _fmt_delta(others_conv[step], sharoon_conv[step])
        print(f"| {step:<14} | {o_count:>8} | {o_conv:>11} | {s_count:>9} | {s_conv:>12} | {delta:>6} |")

    # Insights
    print()
    print("  Insights:")
    for step in FUNNEL_STEPS[1:]:
        oc = others_conv[step]
        sc = sharoon_conv[step]
        if oc is not None and sc is not None:
            delta = sc - oc
            direction = "up" if delta >= 0 else "down"
            sign = "+" if delta >= 0 else ""
            print(f"    \u2022 {step}: {oc:.1f}% (others) vs {sc:.1f}% (Sharoon) [{sign}{delta:.1f}pp] \u2014 {direction}")

    others_e2e = others_m.e2e_rate()
    sharoon_e2e = sharoon_m.e2e_rate()
    if others_e2e is not None and sharoon_e2e is not None:
        print(f"    \u2022 End-to-end: {others_e2e:.1f}% (others) vs {sharoon_e2e:.1f}% (Sharoon)")
    print()


def print_ambassador_breakdown(baseline_rows: List[Row], period_info: PeriodInfo) -> None:
    amb_data = ambassador_breakdown(baseline_rows)
    total = FunnelMetrics(baseline_rows)

    print()
    print(f"  Per-Ambassador Funnel \u2014 Others (no map)")
    print(f"  {period_info.range_str} ({period_info.num_days} day{'s' if period_info.num_days != 1 else ''})")
    print()

    print(f"| {'Ambassador':<20} | {'Visits':>6} | {'Opener Conv':>11} | {'Demos':>5} | {'Demo Conv':>9} | {'Onboard':>7} | {'E2E %':>6} |")
    print(f"|{'-'*22}|{'-'*8}|{'-'*13}|{'-'*7}|{'-'*11}|{'-'*9}|{'-'*8}|")

    for name, m in amb_data:
        if m.visits == 0:
            continue
        opener_pct = _fmt_conv(_conv_rate(m.opener_passed, m.visits))
        demo_pct = _fmt_conv(_conv_rate(m.demos, m.opener_passed))
        e2e_pct = _fmt_conv(_conv_rate(m.onboardings, m.visits))
        print(f"| {name:<20} | {m.visits:>6} | {opener_pct:>11} | {m.demos:>5} | {demo_pct:>9} | {m.onboardings:>7} | {e2e_pct:>6} |")

    # Total row
    t_opener = _fmt_conv(_conv_rate(total.opener_passed, total.visits))
    t_demo = _fmt_conv(_conv_rate(total.demos, total.opener_passed))
    t_e2e = _fmt_conv(_conv_rate(total.onboardings, total.visits))
    print(f"| {'TOTAL':<20} | {total.visits:>6} | {t_opener:>11} | {total.demos:>5} | {t_demo:>9} | {total.onboardings:>7} | {t_e2e:>6} |")
    print()

    # Insights
    print("  Insights:")
    qualified = [(n, m) for n, m in amb_data if m.visits >= MIN_VISITS_FOR_INSIGHT]

    if qualified:
        best_opener = max(qualified, key=lambda x: _conv_rate(x[1].opener_passed, x[1].visits) or 0)
        print(f"    \u2022 Highest opener: {best_opener[0]} ({_fmt_conv(_conv_rate(best_opener[1].opener_passed, best_opener[1].visits))})")

        with_demos = [(n, m) for n, m in qualified if m.opener_passed > 0]
        if with_demos:
            best_demo = max(with_demos, key=lambda x: _conv_rate(x[1].demos, x[1].opener_passed) or 0)
            print(f"    \u2022 Highest demo conv: {best_demo[0]} ({_fmt_conv(_conv_rate(best_demo[1].demos, best_demo[1].opener_passed))})")

        best_e2e = max(qualified, key=lambda x: _conv_rate(x[1].onboardings, x[1].visits) or 0)
        print(f"    \u2022 Best E2E: {best_e2e[0]} ({_fmt_conv(_conv_rate(best_e2e[1].onboardings, best_e2e[1].visits))}) [excl. <{MIN_VISITS_FOR_INSIGHT} visits]")

    overall_e2e = _conv_rate(total.onboardings, total.visits)
    print(f"    \u2022 End-to-end (visits \u2192 onboarded): {_fmt_conv(overall_e2e)}")

    if period_info.num_days > 0:
        daily_avg = total.onboardings / period_info.num_days
        print(f"    \u2022 Daily avg onboardings: {daily_avg:.1f}/day across {period_info.num_days} day{'s' if period_info.num_days != 1 else ''}")

    print()
