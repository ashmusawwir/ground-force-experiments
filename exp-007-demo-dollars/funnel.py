"""Pure computation — retargeting analysis grouping."""

from collections import defaultdict

from data import (
    row_date, is_onboarding, did_demo, did_onboard,
    ambassador_name, phone_number, db_demo_date, db_onboard_date,
    _db_status,
)


class MerchantJourney:
    """All visits for a single merchant phone number."""

    def __init__(self, phone, rows):
        self.phone = phone
        self.rows = rows

        dates_rows = []
        for r in rows:
            d = row_date(r)
            if d:
                dates_rows.append((d, r))
        dates_rows.sort(key=lambda x: x[0])

        self.visit_dates = sorted(set(d for d, _ in dates_rows))
        self.first_date = self.visit_dates[0] if self.visit_dates else None

        first_rows = [r for d, r in dates_rows if d == self.first_date]
        sample_row = first_rows[0] if first_rows else rows[0]

        if _db_status:
            # DB mode: use DB verdicts with date comparison
            self.demoed_first = did_demo(sample_row)
            demo_dt = db_demo_date(sample_row)
            if demo_dt and self.first_date and demo_dt > self.first_date:
                self.demoed_first = False  # demo came after first visit

            onboard_dt = db_onboard_date(sample_row)
            self.onboarded_first = did_onboard(sample_row) and (
                onboard_dt is not None and self.first_date is not None
                and onboard_dt <= self.first_date
            )
            self.ever_onboarded = did_onboard(sample_row)
        else:
            # Sheet fallback
            self.demoed_first = any(did_demo(r) for r in first_rows)
            self.onboarded_first = any(did_onboard(r) for r in first_rows)
            self.ever_onboarded = any(did_onboard(r) for r in rows)

        self.ambassador = ambassador_name(first_rows[0]) if first_rows else "Unknown"

        self.num_visit_days = len(self.visit_dates)
        self.was_retargeted = self.num_visit_days > 1

        if self.was_retargeted and self.first_date:
            self.days_to_revisit = (self.visit_dates[1] - self.first_date).days
        else:
            self.days_to_revisit = None

    @property
    def in_retarget_pool(self):
        """Demoed on first visit but did NOT onboard."""
        return self.demoed_first and not self.onboarded_first


class RetargetingMetrics:
    """Aggregate retargeting metrics."""

    def __init__(self, journeys):
        self.total_merchants = len(journeys)
        self.demoed = sum(1 for j in journeys if j.demoed_first)
        self.onboarded_first = sum(1 for j in journeys if j.onboarded_first)
        self.not_demoed = sum(1 for j in journeys if not j.demoed_first)

        pool = [j for j in journeys if j.in_retarget_pool]
        self.pool_size = len(pool)

        retargeted = [j for j in pool if j.was_retargeted]
        not_retargeted = [j for j in pool if not j.was_retargeted]

        self.retargeted_count = len(retargeted)
        self.not_retargeted_count = len(not_retargeted)

        self.retargeted_converted = sum(1 for j in retargeted if j.ever_onboarded)
        self.not_retargeted_converted = sum(1 for j in not_retargeted if j.ever_onboarded)

        self.retargeted_rate = (
            self.retargeted_converted / self.retargeted_count * 100
            if self.retargeted_count else None
        )
        self.not_retargeted_rate = (
            self.not_retargeted_converted / self.not_retargeted_count * 100
            if self.not_retargeted_count else None
        )

        self.overall_pool_converted = self.retargeted_converted + self.not_retargeted_converted
        self.overall_pool_rate = (
            self.overall_pool_converted / self.pool_size * 100
            if self.pool_size else None
        )

        self.days_distribution = defaultdict(int)
        for j in retargeted:
            if j.days_to_revisit is not None:
                if j.days_to_revisit <= 3:
                    self.days_distribution["1-3 days"] += 1
                elif j.days_to_revisit <= 7:
                    self.days_distribution["4-7 days"] += 1
                elif j.days_to_revisit <= 14:
                    self.days_distribution["8-14 days"] += 1
                else:
                    self.days_distribution["15+ days"] += 1


class PeriodInfo:
    """Date range and day count for a set of rows."""

    def __init__(self, rows):
        dates = set()
        for row in rows:
            d = row_date(row)
            if d:
                dates.add(d)
        self.num_days = len(dates)
        if dates:
            lo, hi = min(dates), max(dates)
            lo_s, hi_s = lo.strftime("%b %d"), hi.strftime("%b %d")
            self.range_str = f"{lo_s} \u2013 {hi_s}" if lo_s != hi_s else lo_s
        else:
            self.range_str = "no data"


def build_journeys(rows):
    """Group onboarding rows by phone -> MerchantJourney list."""
    onb = [r for r in rows if is_onboarding(r)]
    by_phone = defaultdict(list)
    for r in onb:
        p = phone_number(r)
        if p:
            by_phone[p].append(r)
    return [MerchantJourney(phone, phone_rows) for phone, phone_rows in by_phone.items()]


def ambassador_breakdown(journeys):
    """Per-ambassador retargeting metrics, sorted by pool size descending."""
    by_amb = defaultdict(list)
    for j in journeys:
        if j.in_retarget_pool:
            by_amb[j.ambassador].append(j)

    result = []
    for name, pool_journeys in by_amb.items():
        retargeted = [j for j in pool_journeys if j.was_retargeted]
        not_retargeted = [j for j in pool_journeys if not j.was_retargeted]

        rt_conv = sum(1 for j in retargeted if j.ever_onboarded)
        nrt_conv = sum(1 for j in not_retargeted if j.ever_onboarded)

        rt_rate = rt_conv / len(retargeted) * 100 if retargeted else None
        nrt_rate = nrt_conv / len(not_retargeted) * 100 if not_retargeted else None

        result.append({
            "name": name,
            "pool": len(pool_journeys),
            "retargeted": len(retargeted),
            "not_retargeted": len(not_retargeted),
            "rt_converted": rt_conv,
            "nrt_converted": nrt_conv,
            "rt_rate": rt_rate,
            "nrt_rate": nrt_rate,
        })

    result.sort(key=lambda x: x["pool"], reverse=True)
    return result


def no_phone_count(rows):
    """Count onboarding rows without a phone number (data quality metric)."""
    onb = [r for r in rows if is_onboarding(r)]
    return sum(1 for r in onb if not phone_number(r))


def phone_audit(rows):
    """Phone coverage audit: per-ambassador and per-date breakdowns."""
    onb = [r for r in rows if is_onboarding(r)]

    by_ambassador = defaultdict(lambda: {"total": 0, "has_phone": 0})
    by_date = defaultdict(lambda: {"total": 0, "has_phone": 0})

    for r in onb:
        amb = ambassador_name(r)
        d = row_date(r)
        has_ph = bool(phone_number(r))

        by_ambassador[amb]["total"] += 1
        if has_ph:
            by_ambassador[amb]["has_phone"] += 1

        if d:
            ds = d.strftime("%Y-%m-%d")
            by_date[ds]["total"] += 1
            if has_ph:
                by_date[ds]["has_phone"] += 1

    amb_audit = []
    for name, stats in sorted(by_ambassador.items()):
        pct = stats["has_phone"] / stats["total"] * 100 if stats["total"] else 0
        amb_audit.append({
            "name": name,
            "total": stats["total"],
            "has_phone": stats["has_phone"],
            "pct": pct,
        })
    amb_audit.sort(key=lambda x: x["total"], reverse=True)

    date_audit = []
    for ds, stats in sorted(by_date.items()):
        pct = stats["has_phone"] / stats["total"] * 100 if stats["total"] else 0
        date_audit.append({
            "date": ds,
            "total": stats["total"],
            "has_phone": stats["has_phone"],
            "pct": pct,
        })

    return {"by_ambassador": amb_audit, "by_date": date_audit}
