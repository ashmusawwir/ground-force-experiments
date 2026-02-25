"""All terminal printing — tables, insights, formatting helpers."""

from config import EXPERIMENT_NAME
from funnel import RetargetingMetrics, PeriodInfo, ambassador_breakdown


def _sig2(x):
    """Format a number to 2 significant digits (e.g. 18, 5.9, 0.73)."""
    s = f"{x:.2g}"
    return f"{x:.0f}" if "e" in s else s


def _fmt(rate):
    return f"{_sig2(rate)}%" if rate is not None else "\u2014"


def print_data_quality(total_onboarding, no_phone, info):
    print()
    print(f"  {EXPERIMENT_NAME}")
    print(f"  Period: {info.range_str} ({info.num_days} days)")
    print()
    has_phone = total_onboarding - no_phone
    pct = has_phone / total_onboarding * 100 if total_onboarding else 0
    print(f"  Data Quality:")
    print(f"    Total onboarding visits: {total_onboarding}")
    print(f"    With phone number:       {has_phone} ({_sig2(pct)}%)")
    print(f"    Missing phone:           {no_phone}")
    print()


def print_phone_audit(audit):
    """Print per-ambassador and per-date phone coverage tables."""
    amb = audit["by_ambassador"]
    dates = audit["by_date"]

    print(f"  Phone Audit — By Ambassador")
    print()
    print(f"| {'Ambassador':<20} | {'Total':>6} | {'w/ Phone':>8} | {'Coverage':>8} |")
    print(f"|{'-'*22}|{'-'*8}|{'-'*10}|{'-'*10}|")
    for a in amb:
        print(f"| {a['name']:<20} | {a['total']:>6} | {a['has_phone']:>8} | {_sig2(a['pct']):>7}% |")
    total_t = sum(a["total"] for a in amb)
    total_p = sum(a["has_phone"] for a in amb)
    total_pct = total_p / total_t * 100 if total_t else 0
    print(f"| {'TOTAL':<20} | {total_t:>6} | {total_p:>8} | {_sig2(total_pct):>7}% |")
    print()

    print(f"  Phone Audit — By Date")
    print()
    print(f"| {'Date':<12} | {'Total':>6} | {'w/ Phone':>8} | {'Coverage':>8} |")
    print(f"|{'-'*14}|{'-'*8}|{'-'*10}|{'-'*10}|")
    for d in dates:
        print(f"| {d['date']:<12} | {d['total']:>6} | {d['has_phone']:>8} | {_sig2(d['pct']):>7}% |")
    print()


def print_retargeting_funnel(metrics, journeys):
    print(f"| {'Stage':<32} | {'Count':>6} | {'Rate':>8} |")
    print(f"|{'-'*34}|{'-'*8}|{'-'*10}|")

    demo_rate = metrics.demoed / metrics.total_merchants * 100 if metrics.total_merchants else 0
    onb_rate = metrics.onboarded_first / metrics.total_merchants * 100 if metrics.total_merchants else 0
    pool_pct = metrics.pool_size / metrics.total_merchants * 100 if metrics.total_merchants else 0
    rt_pct = metrics.retargeted_count / metrics.pool_size * 100 if metrics.pool_size else 0

    rows = [
        ("Unique merchants (with phone)", metrics.total_merchants, ""),
        ("Demoed on first visit", metrics.demoed, _fmt(demo_rate)),
        ("Onboarded on first visit", metrics.onboarded_first, _fmt(onb_rate)),
        ("Retarget pool (demo, no onb)", metrics.pool_size, _fmt(pool_pct)),
        ("  Retargeted (2+ visit days)", metrics.retargeted_count, _fmt(rt_pct)),
        ("  Not retargeted (1 day only)", metrics.not_retargeted_count, ""),
    ]

    for label, count, rate in rows:
        print(f"| {label:<32} | {count:>6} | {rate:>8} |")
    print()


def print_conversion_comparison(metrics):
    print(f"  Retargeting vs No Retargeting \u2014 Conversion Comparison")
    print()
    print(f"| {'Group':<24} | {'N':>5} | {'Converted':>10} | {'Rate':>8} |")
    print(f"|{'-'*26}|{'-'*7}|{'-'*12}|{'-'*10}|")

    print(f"| {'Retargeted':<24} | {metrics.retargeted_count:>5} | {metrics.retargeted_converted:>10} | {_fmt(metrics.retargeted_rate):>8} |")
    print(f"| {'Not retargeted':<24} | {metrics.not_retargeted_count:>5} | {metrics.not_retargeted_converted:>10} | {_fmt(metrics.not_retargeted_rate):>8} |")
    print(f"| {'Pool total':<24} | {metrics.pool_size:>5} | {metrics.overall_pool_converted:>10} | {_fmt(metrics.overall_pool_rate):>8} |")
    print()

    print("  Insights:")
    if metrics.retargeted_rate is not None and metrics.not_retargeted_rate is not None:
        delta = metrics.retargeted_rate - metrics.not_retargeted_rate
        sign = "+" if delta >= 0 else ""
        direction = "higher" if delta > 0 else "lower" if delta < 0 else "same"
        print(f"    \u2022 Retargeted conversion {_fmt(metrics.retargeted_rate)} vs not-retargeted {_fmt(metrics.not_retargeted_rate)} ({sign}{_sig2(delta)}pp) \u2014 {direction}")
    elif metrics.retargeted_count == 0:
        print(f"    \u2022 No retargeted merchants found in data")
    print()


def print_ambassador_breakdown(journeys):
    amb_data = ambassador_breakdown(journeys)
    if not amb_data:
        return

    print(f"  Per-Ambassador Retargeting")
    print()
    print(f"| {'Ambassador':<20} | {'Pool':>5} | {'Retgt':>6} | {'RT Conv':>8} | {'No-RT Conv':>10} |")
    print(f"|{'-'*22}|{'-'*7}|{'-'*8}|{'-'*10}|{'-'*12}|")

    for a in amb_data:
        rt_str = f"{a['rt_converted']}/{a['retargeted']}" if a['retargeted'] else "\u2014"
        nrt_str = f"{a['nrt_converted']}/{a['not_retargeted']}" if a['not_retargeted'] else "\u2014"
        print(f"| {a['name']:<20} | {a['pool']:>5} | {a['retargeted']:>6} | {rt_str:>8} | {nrt_str:>10} |")
    print()


def print_days_distribution(metrics):
    if not metrics.days_distribution:
        return

    print(f"  Days to First Revisit")
    print()
    print(f"| {'Bucket':<16} | {'Count':>6} |")
    print(f"|{'-'*18}|{'-'*8}|")

    for bucket in ["1-3 days", "4-7 days", "8-14 days", "15+ days"]:
        count = metrics.days_distribution.get(bucket, 0)
        if count:
            print(f"| {bucket:<16} | {count:>6} |")
    print()
