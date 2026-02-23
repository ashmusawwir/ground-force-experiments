"""Pure computation — no I/O, no printing."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from math import lgamma, exp, log
from typing import Dict, List, Optional, Tuple

from data import (
    Row, row_date, row_hour, row_hour_float, row_datetime,
    is_onboarding, opener_passed, did_demo, did_onboard,
    ambassador_name, ambassador_city, time_bucket, time_window,
)
from config import FUNNEL_STEPS, CITY_BUCKETS, RAMADAN_START


# ── Core funnel ────────────────────────────────────────────────────

class FunnelMetrics:
    """Four-step funnel counts for a set of rows."""

    def __init__(self, rows: List[Row]):
        onb = [r for r in rows if is_onboarding(r)]
        self.visits = len(onb)
        self.opener_passed = sum(1 for r in onb if opener_passed(r))
        self.demos = sum(1 for r in onb if did_demo(r))
        self.onboardings = sum(1 for r in onb if did_onboard(r))

    def as_dict(self) -> dict:
        return dict(zip(FUNNEL_STEPS,
                        [self.visits, self.opener_passed, self.demos, self.onboardings]))

    def step_conversions(self) -> dict:
        d = self.as_dict()
        result = {"Visits": None}
        for i in range(1, len(FUNNEL_STEPS)):
            cur, prev = FUNNEL_STEPS[i], FUNNEL_STEPS[i - 1]
            result[cur] = d[cur] / d[prev] * 100 if d[prev] else None
        return result

    def e2e_rate(self) -> Optional[float]:
        return self.onboardings / self.visits * 100 if self.visits else None


class PeriodInfo:
    """Date range and day count for a set of rows."""

    def __init__(self, rows: List[Row]):
        dates = set()
        for row in rows:
            d = row_date(row)
            if d:
                dates.add(d)
        self.num_days = len(dates)
        if dates:
            lo, hi = min(dates), max(dates)
            lo_s, hi_s = lo.strftime("%b %d"), hi.strftime("%b %d")
            self.range_str = f"{lo_s} - {hi_s}" if lo_s != hi_s else lo_s
        else:
            self.range_str = "no data"


def ambassador_breakdown(rows: List[Row]) -> List[Tuple[str, FunnelMetrics]]:
    """Per-ambassador funnel metrics, sorted by visits descending."""
    by_amb: Dict[str, List[Row]] = defaultdict(list)
    for row in rows:
        by_amb[ambassador_name(row)].append(row)
    result = [(name, FunnelMetrics(amb_rows)) for name, amb_rows in by_amb.items()]
    result.sort(key=lambda x: -x[1].visits)
    return result


# ── Bayesian helpers ───────────────────────────────────────────────

def _log_beta(a: float, b: float) -> float:
    """Log of Beta function: B(a, b) = Gamma(a)*Gamma(b)/Gamma(a+b)."""
    return lgamma(a) + lgamma(b) - lgamma(a + b)


def bayesian_p_better(s1: int, n1: int, s2: int, n2: int,
                      samples: int = 50000) -> float:
    """P(rate2 > rate1) using Beta-Binomial closed-form grid approximation.

    s1, n1 = successes and trials for group 1 (baseline/daytime)
    s2, n2 = successes and trials for group 2 (treatment/nighttime)
    Returns probability that group 2's true rate > group 1's true rate.
    """
    if n1 == 0 or n2 == 0:
        return 0.5
    # Use Monte Carlo with Beta posteriors
    import random
    random.seed(42)
    a1, b1 = s1 + 1, n1 - s1 + 1  # Beta posterior (uniform prior)
    a2, b2 = s2 + 1, n2 - s2 + 1
    count = 0
    for _ in range(samples):
        r1 = random.betavariate(a1, b1)
        r2 = random.betavariate(a2, b2)
        if r2 > r1:
            count += 1
    return count / samples


def wilson_ci(successes: int, trials: int, z: float = 1.96) -> Tuple[float, float]:
    """Wilson score 95% confidence interval for a proportion."""
    if trials == 0:
        return (0.0, 0.0)
    p = successes / trials
    denom = 1 + z * z / trials
    centre = p + z * z / (2 * trials)
    spread = z * ((p * (1 - p) / trials + z * z / (4 * trials * trials)) ** 0.5)
    lo = max(0.0, (centre - spread) / denom) * 100
    hi = min(1.0, (centre + spread) / denom) * 100
    return (lo, hi)


# ── Informative Bayesian priors (pre-Ramadan data) ────────────────

# Pre-Ramadan baseline constants (from 1,111 pre-Ramadan visits)
PRE_DAY_ONB = 20       # daytime (<5pm) onboards
PRE_DAY_VISITS = 489   # daytime visits
PRE_NIGHT_ONB = 50     # evening (5pm+) onboards
PRE_NIGHT_VISITS = 622 # evening visits


def bayesian_p_with_prior(
    ram_day_onb: int, ram_day_visits: int,
    ram_night_onb: int, ram_night_visits: int,
    pre_day_onb: int = PRE_DAY_ONB, pre_day_visits: int = PRE_DAY_VISITS,
    pre_night_onb: int = PRE_NIGHT_ONB, pre_night_visits: int = PRE_NIGHT_VISITS,
    samples: int = 50000,
) -> float:
    """P(night > day) using Beta posteriors with pre-Ramadan informative priors.

    Prior for daytime  = Beta(pre_day_onb + 1, pre_day_visits - pre_day_onb + 1)
    Prior for nighttime = Beta(pre_night_onb + 1, pre_night_visits - pre_night_onb + 1)
    Posterior updates with Ramadan observations.
    """
    if ram_day_visits == 0 and ram_night_visits == 0:
        # No Ramadan data yet — use prior only
        a_day = pre_day_onb + 1
        b_day = pre_day_visits - pre_day_onb + 1
        a_night = pre_night_onb + 1
        b_night = pre_night_visits - pre_night_onb + 1
    else:
        # Posterior = Beta(prior_a + ram_successes, prior_b + ram_failures)
        a_day = pre_day_onb + ram_day_onb + 1
        b_day = (pre_day_visits - pre_day_onb) + (ram_day_visits - ram_day_onb) + 1
        a_night = pre_night_onb + ram_night_onb + 1
        b_night = (pre_night_visits - pre_night_onb) + (ram_night_visits - ram_night_onb) + 1

    import random
    random.seed(42)
    count = 0
    for _ in range(samples):
        r_day = random.betavariate(a_day, b_day)
        r_night = random.betavariate(a_night, b_night)
        if r_night > r_day:
            count += 1
    return count / samples


def bayesian_p_vs_baseline(
    ram_night_onb: int, ram_night_visits: int,
    baseline_rate: float = PRE_NIGHT_ONB / PRE_NIGHT_VISITS,  # 8.04%
    samples: int = 50000,
) -> float:
    """P(Ramadan nighttime rate >= baseline_rate). One-sided.

    Uses uninformative prior for the Ramadan nighttime rate to keep this
    comparison independent of the prior-informed day-vs-night test.
    """
    if ram_night_visits == 0:
        return 0.5
    import random
    random.seed(43)
    a = ram_night_onb + 1
    b = ram_night_visits - ram_night_onb + 1
    count = 0
    for _ in range(samples):
        r = random.betavariate(a, b)
        if r >= baseline_rate:
            count += 1
    return count / samples


# ── Sequential credibility monitoring ─────────────────────────────

@dataclass
class DailyCredibility:
    """One row in the sequential monitor table."""
    day: date
    cum_day_visits: int
    cum_day_onb: int
    cum_night_visits: int
    cum_night_onb: int
    p_with_prior: float       # P(night > day) with informative prior
    p_uninformative: float    # P(night > day) with uniform prior (for comparison)
    p_vs_baseline: float      # P(night >= pre-Ramadan evening)
    verdict: str              # "Strong" / "Likely" / "Directional" / "Insufficient"


def _verdict_label(p: float) -> str:
    if p >= 0.95:
        return "Strong"
    if p >= 0.80:
        return "Likely"
    if p >= 0.50:
        return "Directional"
    return "Insufficient"


def sequential_credibility(
    ramadan_rows: List[Row],
) -> List[DailyCredibility]:
    """Compute daily cumulative P values for sequential monitoring.

    Groups Ramadan visits by date, classifies into day/night windows,
    and computes cumulative Bayesian P values each day.
    """
    from data import row_date, is_onboarding, did_onboard, row_hour_float, ambassador_city, time_window as tw

    # Group rows by date, classified into day/night
    daily: Dict[date, Dict[str, Tuple[int, int]]] = defaultdict(
        lambda: {"day": (0, 0), "night": (0, 0)}
    )

    for row in ramadan_rows:
        if not is_onboarding(row):
            continue
        d = row_date(row)
        hf = row_hour_float(row)
        if d is None or hf is None:
            continue
        city = ambassador_city(row)
        w = tw(hf, city)
        onb = 1 if did_onboard(row) else 0
        if w == "Daytime":
            v, o = daily[d]["day"]
            daily[d]["day"] = (v + 1, o + onb)
        elif w == "Nighttime":
            v, o = daily[d]["night"]
            daily[d]["night"] = (v + 1, o + onb)
        # Evening Transition visits are excluded from day/night comparison

    if not daily:
        return []

    # Build cumulative trajectory
    result = []
    cum_dv = cum_do = cum_nv = cum_no = 0

    for d in sorted(daily.keys()):
        dv, do_ = daily[d]["day"]
        nv, no_ = daily[d]["night"]
        cum_dv += dv
        cum_do += do_
        cum_nv += nv
        cum_no += no_

        p_prior = bayesian_p_with_prior(cum_do, cum_dv, cum_no, cum_nv)
        p_flat = bayesian_p_better(cum_do, cum_dv, cum_no, cum_nv)
        p_base = bayesian_p_vs_baseline(cum_no, cum_nv)

        result.append(DailyCredibility(
            day=d,
            cum_day_visits=cum_dv,
            cum_day_onb=cum_do,
            cum_night_visits=cum_nv,
            cum_night_onb=cum_no,
            p_with_prior=p_prior,
            p_uninformative=p_flat,
            p_vs_baseline=p_base,
            verdict=_verdict_label(p_prior),
        ))

    return result


def credibility_estimate(
    trajectory: List[DailyCredibility],
    target_p: float = 0.95,
) -> Optional[int]:
    """Rough estimate: how many more days to reach target credibility?

    Uses linear extrapolation of the P trajectory. Returns None if
    already at target, trajectory is empty, or estimate would be > 30 days.
    """
    if not trajectory:
        return None

    latest = trajectory[-1]
    if latest.p_with_prior >= target_p:
        return 0  # already there

    if len(trajectory) < 2:
        return None  # can't extrapolate from 1 point

    # Linear rate of P increase per day
    first = trajectory[0]
    days_elapsed = len(trajectory)
    p_delta = latest.p_with_prior - first.p_with_prior

    if p_delta <= 0:
        return None  # not improving

    p_per_day = p_delta / days_elapsed
    remaining_p = target_p - latest.p_with_prior
    est_days = int(remaining_p / p_per_day + 0.5)

    return est_days if est_days <= 30 else None


# ── Time bucket metrics ────────────────────────────────────────────

@dataclass
class TimeBucketMetrics:
    bucket_name: str
    visits: int = 0
    opener_passed: int = 0
    demos: int = 0
    onboards: int = 0

    @property
    def opener_rate(self) -> Optional[float]:
        return self.opener_passed / self.visits * 100 if self.visits else None

    @property
    def demo_rate(self) -> Optional[float]:
        return self.demos / self.visits * 100 if self.visits else None

    @property
    def onboard_rate(self) -> Optional[float]:
        return self.onboards / self.visits * 100 if self.visits else None

    @property
    def e2e_rate(self) -> Optional[float]:
        return self.onboards / self.visits * 100 if self.visits else None

    def e2e_ci(self) -> Tuple[float, float]:
        return wilson_ci(self.onboards, self.visits)


def bucket_breakdown(rows: List[Row], city: str = "Karachi") -> List[TimeBucketMetrics]:
    """Per-bucket funnel metrics for the given city."""
    onb = [r for r in rows if is_onboarding(r)]
    buckets_order = [name for name, _, _ in CITY_BUCKETS.get(city, CITY_BUCKETS["Karachi"])]
    by_bucket: Dict[str, List[Row]] = defaultdict(list)

    for row in onb:
        hf = row_hour_float(row)
        if hf is None:
            continue
        b = time_bucket(hf, city)
        by_bucket[b].append(row)

    result = []
    for bname in buckets_order:
        brows = by_bucket.get(bname, [])
        m = TimeBucketMetrics(
            bucket_name=bname,
            visits=len(brows),
            opener_passed=sum(1 for r in brows if opener_passed(r)),
            demos=sum(1 for r in brows if did_demo(r)),
            onboards=sum(1 for r in brows if did_onboard(r)),
        )
        result.append(m)
    return result


# ── Window comparison ──────────────────────────────────────────────

@dataclass
class WindowComparison:
    """Daytime vs Nighttime comparison with Bayesian test."""
    day_metrics: FunnelMetrics
    evening_metrics: FunnelMetrics
    night_metrics: FunnelMetrics
    p_night_better_than_day: float = 0.5         # P(night > day) uniform prior
    p_night_better_with_prior: float = 0.5       # P(night > day) informative prior
    p_vs_pre_ramadan_baseline: float = 0.5       # P(night >= pre-Ramadan evening)


def window_comparison(day_rows: List[Row], evening_rows: List[Row],
                      night_rows: List[Row]) -> WindowComparison:
    """Compute window comparison with Bayesian credibility."""
    dm = FunnelMetrics(day_rows)
    em = FunnelMetrics(evening_rows)
    nm = FunnelMetrics(night_rows)
    p_flat = bayesian_p_better(dm.onboardings, dm.visits, nm.onboardings, nm.visits)
    p_prior = bayesian_p_with_prior(
        dm.onboardings, dm.visits, nm.onboardings, nm.visits,
    )
    p_baseline = bayesian_p_vs_baseline(nm.onboardings, nm.visits)
    return WindowComparison(
        day_metrics=dm,
        evening_metrics=em,
        night_metrics=nm,
        p_night_better_than_day=p_flat,
        p_night_better_with_prior=p_prior,
        p_vs_pre_ramadan_baseline=p_baseline,
    )


# ── Productivity metrics ───────────────────────────────────────────

@dataclass
class ProductivityMetrics:
    ambassador: str
    city: str
    visits: int = 0
    onboardings: int = 0
    num_days: int = 0
    first_hour: Optional[float] = None
    last_hour: Optional[float] = None
    day_visits: int = 0
    night_visits: int = 0

    @property
    def visits_per_day(self) -> Optional[float]:
        return self.visits / self.num_days if self.num_days else None

    @property
    def onboards_per_day(self) -> Optional[float]:
        return self.onboardings / self.num_days if self.num_days else None

    @property
    def active_hours(self) -> Optional[float]:
        if self.first_hour is not None and self.last_hour is not None:
            return self.last_hour - self.first_hour
        return None

    @property
    def preference(self) -> str:
        """Day/Night preference based on visit split."""
        total = self.day_visits + self.night_visits
        if total == 0:
            return "—"
        night_pct = self.night_visits / total * 100
        if night_pct >= 60:
            return "Night"
        elif night_pct <= 40:
            return "Day"
        return "Mixed"

    @property
    def tier(self) -> str:
        if self.visits >= 20:
            return "Reliable"
        if self.visits >= 5:
            return "Directional"
        return "Insufficient"


def productivity_summary(rows: List[Row]) -> List[ProductivityMetrics]:
    """Per-ambassador productivity: visits/day, onboardings/day, active hours."""
    onb = [r for r in rows if is_onboarding(r)]
    by_amb: Dict[str, List[Row]] = defaultdict(list)
    for row in onb:
        by_amb[ambassador_name(row)].append(row)

    result = []
    for name, amb_rows in by_amb.items():
        dates = set()
        hours = []
        day_v = night_v = 0
        city = "Karachi"  # default, will be overridden per-row

        for row in amb_rows:
            d = row_date(row)
            if d:
                dates.add(d)
            hf = row_hour_float(row)
            if hf is not None:
                hours.append(hf)
            city = ambassador_city(row)
            w = time_window(hf, city) if hf is not None else None
            if w == "Daytime":
                day_v += 1
            elif w == "Nighttime":
                night_v += 1

        pm = ProductivityMetrics(
            ambassador=name,
            city=city,
            visits=len(amb_rows),
            onboardings=sum(1 for r in amb_rows if did_onboard(r)),
            num_days=len(dates),
            first_hour=min(hours) if hours else None,
            last_hour=max(hours) if hours else None,
            day_visits=day_v,
            night_visits=night_v,
        )
        result.append(pm)

    result.sort(key=lambda x: -(x.onboardings))
    return result


# ── Hourly heatmap ─────────────────────────────────────────────────

@dataclass
class HourCell:
    visits: int = 0
    onboards: int = 0

    @property
    def e2e_rate(self) -> Optional[float]:
        return self.onboards / self.visits * 100 if self.visits else None


def hourly_heatmap(rows: List[Row]) -> Dict[str, Dict[int, HourCell]]:
    """Ambassador x hour grid. Returns {ambassador: {hour: HourCell}}."""
    onb = [r for r in rows if is_onboarding(r)]
    grid: Dict[str, Dict[int, HourCell]] = defaultdict(lambda: defaultdict(HourCell))

    for row in onb:
        h = row_hour(row)
        if h is None:
            continue
        name = ambassador_name(row)
        grid[name][h].visits += 1
        if did_onboard(row):
            grid[name][h].onboards += 1

    return dict(grid)


def hourly_totals(rows: List[Row]) -> Dict[int, HourCell]:
    """Aggregate hour-level metrics (all ambassadors combined)."""
    onb = [r for r in rows if is_onboarding(r)]
    totals: Dict[int, HourCell] = defaultdict(HourCell)
    for row in onb:
        h = row_hour(row)
        if h is None:
            continue
        totals[h].visits += 1
        if did_onboard(row):
            totals[h].onboards += 1
    return dict(totals)


# ── Fatigue curve ──────────────────────────────────────────────────

def fatigue_curve(rows: List[Row]) -> List[Tuple[int, HourCell]]:
    """Conversion by hour-of-day for all ambassadors (fatigue proxy)."""
    totals = hourly_totals(rows)
    return sorted(totals.items())


# ── Weekly trend ───────────────────────────────────────────────────

@dataclass
class WeekMetrics:
    week_num: int
    start_date: date
    end_date: date
    visits: int = 0
    onboardings: int = 0
    num_days: int = 0

    @property
    def visits_per_day(self) -> Optional[float]:
        return self.visits / self.num_days if self.num_days else None

    @property
    def onboards_per_day(self) -> Optional[float]:
        return self.onboardings / self.num_days if self.num_days else None

    @property
    def e2e_rate(self) -> Optional[float]:
        return self.onboardings / self.visits * 100 if self.visits else None


def weekly_trend(rows: List[Row]) -> List[WeekMetrics]:
    """Week-over-week metrics (week = 7-day block from RAMADAN_START)."""
    onb = [r for r in rows if is_onboarding(r)]
    by_week: Dict[int, List[Row]] = defaultdict(list)
    date_sets: Dict[int, set] = defaultdict(set)

    for row in onb:
        d = row_date(row)
        if d is None or d < RAMADAN_START:
            continue
        week_num = (d - RAMADAN_START).days // 7 + 1
        by_week[week_num].append(row)
        date_sets[week_num].add(d)

    result = []
    for wn in sorted(by_week.keys()):
        wrows = by_week[wn]
        dates = date_sets[wn]
        start = RAMADAN_START + timedelta(days=(wn - 1) * 7)
        end = start + timedelta(days=6)
        wm = WeekMetrics(
            week_num=wn,
            start_date=start,
            end_date=min(end, max(dates)),
            visits=len(wrows),
            onboardings=sum(1 for r in wrows if did_onboard(r)),
            num_days=len(dates),
        )
        result.append(wm)
    return result


# ── City comparison ────────────────────────────────────────────────

def city_breakdown(rows: List[Row]) -> Dict[str, FunnelMetrics]:
    """Per-city funnel metrics."""
    by_city: Dict[str, List[Row]] = defaultdict(list)
    for row in rows:
        city = ambassador_city(row)
        by_city[city].append(row)
    return {city: FunnelMetrics(city_rows) for city, city_rows in by_city.items()}


# ── Schedule shift tracking ────────────────────────────────────────

@dataclass
class DailySchedule:
    day: date
    ambassador: str
    first_hour: Optional[float] = None
    last_hour: Optional[float] = None
    visit_count: int = 0


def daily_schedules(rows: List[Row]) -> List[DailySchedule]:
    """Per-ambassador per-day first/last visit hour and count."""
    onb = [r for r in rows if is_onboarding(r)]
    groups: Dict[Tuple[str, date], List[float]] = defaultdict(list)

    for row in onb:
        d = row_date(row)
        hf = row_hour_float(row)
        if d is None or hf is None:
            continue
        name = ambassador_name(row)
        groups[(name, d)].append(hf)

    result = []
    for (name, d), hours in groups.items():
        result.append(DailySchedule(
            day=d,
            ambassador=name,
            first_hour=min(hours),
            last_hour=max(hours),
            visit_count=len(hours),
        ))
    result.sort(key=lambda x: (x.ambassador, x.day))
    return result
