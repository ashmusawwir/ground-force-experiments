"""All terminal printing — tables, insights, formatting helpers."""

from typing import List, Optional, Tuple, Dict

from config import EXPERIMENT_NAME, FUNNEL_STEPS, MIN_VISITS_FOR_INSIGHT, RAMADAN_START
from funnel import (
    FunnelMetrics, PeriodInfo, ambassador_breakdown, TimeBucketMetrics,
    WindowComparison, ProductivityMetrics, HourCell, WeekMetrics,
    DailyCredibility, wilson_ci,
)
from data import Row


# ── Formatting helpers ─────────────────────────────────────────────

def _sig2(x: float) -> str:
    """Format a number to 2 significant digits (e.g. 18, 5.9, 0.73)."""
    s = f"{x:.2g}"
    return f"{x:.0f}" if "e" in s else s


def _conv_rate(count: int, total: int) -> Optional[float]:
    return count / total * 100 if total else None


def _fmt(rate: Optional[float]) -> str:
    return f"{_sig2(rate)}%" if rate is not None else "\u2014"


def _fmt_delta(base_rate: Optional[float], expt_rate: Optional[float]) -> str:
    if base_rate is None or expt_rate is None:
        return "\u2014"
    d = expt_rate - base_rate
    sign = "+" if d >= 0 else ""
    return f"{sign}{_sig2(d)}pp"


def _fmt_hour(h: Optional[float]) -> str:
    """Format hour float (e.g. 17.5) as '5:30pm'."""
    if h is None:
        return "\u2014"
    hour = int(h)
    minute = int((h - hour) * 60)
    suffix = "am" if hour < 12 else "pm"
    display_h = hour if hour <= 12 else hour - 12
    if display_h == 0:
        display_h = 12
    if minute == 0:
        return f"{display_h}{suffix}"
    return f"{display_h}:{minute:02d}{suffix}"


def _fmt_ci(lo: float, hi: float) -> str:
    return f"[{_sig2(lo)}, {_sig2(hi)}]"


def _credibility_label(p: float) -> str:
    if p >= 0.95:
        return "Strong"
    if p >= 0.80:
        return "Likely"
    return "Directional"


# ── Period comparison ──────────────────────────────────────────────

def print_period_comparison(base_m: FunnelMetrics, ram_m: FunnelMetrics,
                            base_info: PeriodInfo, ram_info: PeriodInfo) -> None:
    base_d, ram_d = base_m.as_dict(), ram_m.as_dict()
    base_conv, ram_conv = base_m.step_conversions(), ram_m.step_conversions()

    print()
    print(f"  {EXPERIMENT_NAME} \u2014 Pre-Ramadan vs Ramadan")
    print(f"  Pre-Ramadan: {base_info.range_str} ({base_info.num_days} days)")
    print(f"  Ramadan:     {ram_info.range_str} ({ram_info.num_days} day{'s' if ram_info.num_days != 1 else ''})")
    print()

    _d = "\u0394"
    print(f"| {'Step':<14} | {'Pre #':>6} | {'Pre Conv':>9} | {'Ram #':>6} | {'Ram Conv':>9} | {_d:>8} |")
    print(f"|{'-'*16}|{'-'*8}|{'-'*11}|{'-'*8}|{'-'*11}|{'-'*10}|")

    for step in FUNNEL_STEPS:
        b = base_d[step]
        r = ram_d[step]
        bc = _fmt(base_conv[step])
        rc = _fmt(ram_conv[step])
        delta = _fmt_delta(base_conv[step], ram_conv[step])
        print(f"| {step:<14} | {b:>6} | {bc:>9} | {r:>6} | {rc:>9} | {delta:>8} |")

    # Insights
    print()
    print("  Insights:")
    base_e2e = base_m.e2e_rate()
    ram_e2e = ram_m.e2e_rate()
    if base_e2e is not None and ram_e2e is not None:
        print(f"    \u2022 E2E: {_sig2(base_e2e)}% pre-Ramadan vs {_sig2(ram_e2e)}% Ramadan ({_fmt_delta(base_e2e, ram_e2e)})")

    if base_info.num_days > 0 and ram_info.num_days > 0:
        base_daily = base_m.visits / base_info.num_days
        ram_daily = ram_m.visits / ram_info.num_days
        print(f"    \u2022 Visits/day: {base_daily:.1f} pre-Ramadan vs {ram_daily:.1f} Ramadan")
        base_ob = base_m.onboardings / base_info.num_days
        ram_ob = ram_m.onboardings / ram_info.num_days
        print(f"    \u2022 Onboardings/day: {base_ob:.1f} pre-Ramadan vs {ram_ob:.1f} Ramadan")
    print()


# ── Bucket breakdown ───────────────────────────────────────────────

def print_bucket_breakdown(buckets: List[TimeBucketMetrics], city: str) -> None:
    print(f"  Time Bucket Breakdown \u2014 {city}")
    print()
    print(f"| {'Bucket':<18} | {'Visits':>6} | {'Opener%':>8} | {'Demo%':>6} | {'Onboard%':>9} | {'E2E%':>5} | {'95% CI':>14} |")
    print(f"|{'-'*20}|{'-'*8}|{'-'*10}|{'-'*8}|{'-'*11}|{'-'*7}|{'-'*16}|")

    for b in buckets:
        ci = b.e2e_ci()
        ci_str = _fmt_ci(ci[0], ci[1]) if b.visits > 0 else "\u2014"
        print(f"| {b.bucket_name:<18} | {b.visits:>6} | {_fmt(b.opener_rate):>8} | {_fmt(b.demo_rate):>6} | {_fmt(b.onboard_rate):>9} | {_fmt(b.e2e_rate):>5} | {ci_str:>14} |")
    print()


# ── Window comparison (Day vs Night) ───────────────────────────────

def print_window_comparison(wc: WindowComparison) -> None:
    print("  Day vs Night Window Comparison")
    print()
    dm, em, nm = wc.day_metrics, wc.evening_metrics, wc.night_metrics

    print(f"| {'Window':<22} | {'Visits':>6} | {'Onboards':>8} | {'E2E%':>6} | {'95% CI':>14} |")
    print(f"|{'-'*24}|{'-'*8}|{'-'*10}|{'-'*8}|{'-'*16}|")

    for label, m in [("Daytime (<Iftar)", dm), ("Evening Transition", em), ("Nighttime (>Taraweeh)", nm)]:
        e2e = m.e2e_rate()
        ci = wilson_ci(m.onboardings, m.visits)
        ci_str = _fmt_ci(ci[0], ci[1]) if m.visits > 0 else "\u2014"
        print(f"| {label:<22} | {m.visits:>6} | {m.onboardings:>8} | {_fmt(e2e):>6} | {ci_str:>14} |")

    # Bayesian verdicts
    p_flat = wc.p_night_better_than_day
    p_prior = wc.p_night_better_with_prior
    p_base = wc.p_vs_pre_ramadan_baseline
    print()
    print(f"  P(Night > Day) uninformative = {p_flat:.1%} — {_credibility_label(p_flat)}")
    print(f"  P(Night > Day) with prior    = {p_prior:.1%} — {_credibility_label(p_prior)}")
    print(f"  P(Night ≥ pre-Ram evening)   = {p_base:.1%} — {_credibility_label(p_base)}")
    print()


# ── Hourly heatmap ─────────────────────────────────────────────────

def print_hourly_heatmap(totals: Dict[int, HourCell]) -> None:
    print("  Hourly Conversion (All Ambassadors)")
    print()
    print(f"| {'Hour':>5} | {'Visits':>6} | {'Onboards':>8} | {'E2E%':>6} | {'Bar':>20} |")
    print(f"|{'-'*7}|{'-'*8}|{'-'*10}|{'-'*8}|{'-'*22}|")

    for h in range(9, 24):
        cell = totals.get(h, HourCell())
        e2e = cell.e2e_rate
        bar_len = int(e2e / 2) if e2e else 0
        bar = "\u2588" * bar_len
        print(f"| {h:>2}:00 | {cell.visits:>6} | {cell.onboards:>8} | {_fmt(e2e):>6} | {bar:<20} |")
    print()


# ── Ambassador summary ─────────────────────────────────────────────

def print_ambassador_summary(prods: List[ProductivityMetrics]) -> None:
    print("  Ambassador Summary")
    print()
    print(f"| {'Ambassador':<18} | {'City':<8} | {'Visits':>6} | {'Onb':>4} | {'V/day':>5} | {'O/day':>5} | {'1st Hr':>7} | {'Last Hr':>8} | {'Pref':>6} | {'Tier':<12} |")
    print(f"|{'-'*20}|{'-'*10}|{'-'*8}|{'-'*6}|{'-'*7}|{'-'*7}|{'-'*9}|{'-'*10}|{'-'*8}|{'-'*14}|")

    for p in prods:
        vpd = f"{p.visits_per_day:.1f}" if p.visits_per_day else "\u2014"
        opd = f"{p.onboards_per_day:.1f}" if p.onboards_per_day else "\u2014"
        fh = _fmt_hour(p.first_hour)
        lh = _fmt_hour(p.last_hour)
        print(f"| {p.ambassador:<18} | {p.city:<8} | {p.visits:>6} | {p.onboardings:>4} | {vpd:>5} | {opd:>5} | {fh:>7} | {lh:>8} | {p.preference:>6} | {p.tier:<12} |")
    print()


# ── Productivity ───────────────────────────────────────────────────

def print_productivity(base_info: PeriodInfo, ram_info: PeriodInfo,
                       base_m: FunnelMetrics, ram_m: FunnelMetrics) -> None:
    print("  Productivity Summary")
    print()
    if base_info.num_days > 0:
        print(f"    Pre-Ramadan: {base_m.visits / base_info.num_days:.1f} visits/day, "
              f"{base_m.onboardings / base_info.num_days:.1f} onboardings/day")
    if ram_info.num_days > 0:
        print(f"    Ramadan:     {ram_m.visits / ram_info.num_days:.1f} visits/day, "
              f"{ram_m.onboardings / ram_info.num_days:.1f} onboardings/day")
    print()


# ── Batch logging warnings ─────────────────────────────────────────

def print_batch_logging_warnings(flags: List[dict]) -> None:
    if not flags:
        print("  Batch Logging: No flags detected \u2714")
        print()
        return

    print(f"  \u26a0 Batch Logging Flags ({len(flags)} clusters detected)")
    print()
    print(f"| {'Ambassador':<18} | {'Date':>10} | {'Count':>5} | {'Timestamps':<30} |")
    print(f"|{'-'*20}|{'-'*12}|{'-'*7}|{'-'*32}|")

    for f in flags:
        d_str = f["date"].strftime("%b %d")
        ts_str = ", ".join(f["timestamps"])
        print(f"| {f['ambassador']:<18} | {d_str:>10} | {f['count']:>5} | {ts_str:<30} |")
    print()


# ── Weekly trend ───────────────────────────────────────────────────

def print_weekly_trend(weeks: List[WeekMetrics]) -> None:
    if not weeks:
        print("  Weekly Trend: No Ramadan weeks yet")
        print()
        return

    print("  Weekly Trend (Ramadan)")
    print()
    print(f"| {'Week':>4} | {'Dates':>16} | {'Days':>4} | {'Visits':>6} | {'Onb':>4} | {'V/day':>5} | {'O/day':>5} | {'E2E%':>6} |")
    print(f"|{'-'*6}|{'-'*18}|{'-'*6}|{'-'*8}|{'-'*6}|{'-'*7}|{'-'*7}|{'-'*8}|")

    for w in weeks:
        dates_str = f"{w.start_date.strftime('%b %d')}-{w.end_date.strftime('%d')}"
        vpd = f"{w.visits_per_day:.1f}" if w.visits_per_day else "\u2014"
        opd = f"{w.onboards_per_day:.1f}" if w.onboards_per_day else "\u2014"
        print(f"| {w.week_num:>4} | {dates_str:>16} | {w.num_days:>4} | {w.visits:>6} | {w.onboardings:>4} | {vpd:>5} | {opd:>5} | {_fmt(w.e2e_rate):>6} |")
    print()


# ── Per-ambassador funnel (standard) ───────────────────────────────

def print_ambassador_breakdown(rows: List[Row], info: PeriodInfo) -> None:
    amb_data = ambassador_breakdown(rows)
    total = FunnelMetrics(rows)

    print()
    print(f"  Per-Ambassador Funnel \u2014 {info.range_str}")
    print()
    print(f"| {'Ambassador':<18} | {'Visits':>6} | {'Opener%':>8} | {'Demo%':>6} | {'Onboard':>7} | {'E2E%':>6} |")
    print(f"|{'-'*20}|{'-'*8}|{'-'*10}|{'-'*8}|{'-'*9}|{'-'*8}|")

    for name, m in amb_data:
        if m.visits == 0:
            continue
        opener_pct = _fmt(_conv_rate(m.opener_passed, m.visits))
        demo_pct = _fmt(_conv_rate(m.demos, m.visits))
        e2e_pct = _fmt(_conv_rate(m.onboardings, m.visits))
        print(f"| {name:<18} | {m.visits:>6} | {opener_pct:>8} | {demo_pct:>6} | {m.onboardings:>7} | {e2e_pct:>6} |")

    t_opener = _fmt(_conv_rate(total.opener_passed, total.visits))
    t_demo = _fmt(_conv_rate(total.demos, total.visits))
    t_e2e = _fmt(_conv_rate(total.onboardings, total.visits))
    print(f"| {'TOTAL':<18} | {total.visits:>6} | {t_opener:>8} | {t_demo:>6} | {total.onboardings:>7} | {t_e2e:>6} |")
    print()


# ── Sequential credibility monitor ───────────────────────────────

def print_sequential_monitor(trajectory: List[DailyCredibility]) -> None:
    if not trajectory:
        print("  Sequential Credibility Monitor: No Ramadan data yet")
        print()
        return

    print("  Sequential Credibility Monitor")
    print()
    print(f"| {'Day':>8} | {'Cum Day V':>9} | {'Cum Night V':>11} | {'P(N>D) prior':>13} | {'P(N>D) flat':>12} | {'P(N≥baseline)':>14} | {'Verdict':<12} |")
    print(f"|{'-'*10}|{'-'*11}|{'-'*13}|{'-'*15}|{'-'*14}|{'-'*16}|{'-'*14}|")

    for dc in trajectory:
        day_str = dc.day.strftime("%b %d")
        v_mark = " ✓" if dc.verdict == "Strong" else ""
        print(
            f"| {day_str:>8} "
            f"| {dc.cum_day_visits:>9} "
            f"| {dc.cum_night_visits:>11} "
            f"| {dc.p_with_prior:>12.0%} "
            f"| {dc.p_uninformative:>11.0%} "
            f"| {dc.p_vs_baseline:>14.0%} "
            f"| {dc.verdict + v_mark:<12} |"
        )
    print()


def print_credibility_estimate(est_days: Optional[int], trajectory: List[DailyCredibility]) -> None:
    if not trajectory:
        return

    latest = trajectory[-1]
    if est_days is not None and est_days == 0:
        print(f"  ✓ Credibility reached: P(Night > Day) = {latest.p_with_prior:.0%} (Strong)")
    elif est_days is not None:
        print(f"  ⏱ At current accumulation rate, ~{est_days} more day{'s' if est_days != 1 else ''} to Strong (P > 95%)")
    else:
        print(f"  ⏱ Insufficient trajectory data to estimate days to credibility")
    print()
