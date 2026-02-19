"""All terminal printing — tables, insights, formatting helpers."""

from config import EXPERIMENT_NAME, FUNNEL_STEPS, MIN_VISITS_FOR_INSIGHT
from funnel import FunnelMetrics, PeriodInfo, ambassador_breakdown
from data import Row
from typing import List, Optional


def _conv_rate(count: int, total: int) -> Optional[float]:
    return count / total * 100 if total else None


def _sig2(x: float) -> str:
    """Format a number to 2 significant digits (e.g. 18, 5.9, 0.73)."""
    s = f"{x:.2g}"
    return f"{x:.0f}" if "e" in s else s


def _fmt_conv(rate: Optional[float]) -> str:
    return f"{_sig2(rate)}%" if rate is not None else "\u2014"


def _fmt_delta(base_rate: Optional[float], expt_rate: Optional[float]) -> str:
    if base_rate is None or expt_rate is None:
        return "\u2014"
    d = expt_rate - base_rate
    sign = "+" if d >= 0 else ""
    return f"{sign}{_sig2(d)}"


def print_funnel_comparison(base_m: FunnelMetrics, expt_m: FunnelMetrics,
                            base_info: PeriodInfo, expt_info: PeriodInfo) -> None:
    base_d, expt_d = base_m.as_dict(), expt_m.as_dict()
    base_conv, expt_conv = base_m.step_conversions(), expt_m.step_conversions()

    print()
    print(f"  {EXPERIMENT_NAME} Experiment")
    print(f"  Baseline:   {base_info.range_str} ({base_info.num_days} days)")
    print(f"  Experiment: {expt_info.range_str} ({expt_info.num_days} day{'s' if expt_info.num_days != 1 else ''})")
    print()
    _delta = "\u0394"
    print(f"| {'Step':<14} | {'Base #':>7} | {'Base Conv':>10} | {'Expt #':>7} | {'Expt Conv':>10} | {_delta:>6} |")
    print(f"|{'-'*16}|{'-'*9}|{'-'*12}|{'-'*9}|{'-'*12}|{'-'*8}|")

    for step in FUNNEL_STEPS:
        b_count = base_d[step]
        e_count = expt_d[step]
        b_conv = _fmt_conv(base_conv[step])
        e_conv = _fmt_conv(expt_conv[step])
        delta = _fmt_delta(base_conv[step], expt_conv[step])
        print(f"| {step:<14} | {b_count:>7} | {b_conv:>10} | {e_count:>7} | {e_conv:>10} | {delta:>6} |")

    # Insights
    print("  Insights:")
    for step in FUNNEL_STEPS[1:]:
        bc = base_conv[step]
        ec = expt_conv[step]
        if bc is not None and ec is not None:
            delta = ec - bc
            direction = "up" if delta >= 0 else "down"
            sign = "+" if delta >= 0 else ""
            print(f"    \u2022 {step}: {_sig2(bc)}% \u2192 {_sig2(ec)}% ({sign}{_sig2(delta)}pp) \u2014 {direction}")

    base_e2e = base_m.e2e_rate()
    expt_e2e = expt_m.e2e_rate()
    if base_e2e is not None and expt_e2e is not None:
        print(f"    \u2022 End-to-end (visits \u2192 onboarded): {_sig2(base_e2e)}% baseline vs {_sig2(expt_e2e)}% experiment")

    if base_info.num_days > 0 and expt_info.num_days > 0:
        base_daily = base_m.onboardings / base_info.num_days
        expt_daily = expt_m.onboardings / expt_info.num_days
        print(f"    \u2022 Daily avg onboardings: {base_daily:.1f}/day baseline vs {expt_daily:.1f}/day experiment")

    print()


def print_ambassador_breakdown(experiment_rows: List[Row], expt_info: PeriodInfo) -> None:
    amb_data = ambassador_breakdown(experiment_rows)
    total = FunnelMetrics(experiment_rows)

    print()
    print(f"  Per-Ambassador Funnel \u2014 {EXPERIMENT_NAME} Experiment")
    print(f"  {expt_info.range_str} ({expt_info.num_days} day{'s' if expt_info.num_days != 1 else ''})")
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

    if expt_info.num_days > 0:
        daily_avg = total.onboardings / expt_info.num_days
        print(f"    \u2022 Daily avg onboardings: {daily_avg:.1f}/day across {expt_info.num_days} day{'s' if expt_info.num_days != 1 else ''}")

    print()
