"""Pure computation — no I/O, no printing."""

from collections import Counter, defaultdict
from typing import List, Optional, Tuple

from data import (
    Row, row_date, is_onboarding, opener_passed, has_question,
    did_demo, did_onboard, ambassador_name, question_text, split_questions,
)
from config import FUNNEL_STEPS, MAX_DROPOFF_QUESTIONS


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
        """Step-over-step conversion rates (None for Visits)."""
        d = self.as_dict()
        result = {"Visits": None}
        for i in range(1, len(FUNNEL_STEPS)):
            cur, prev = FUNNEL_STEPS[i], FUNNEL_STEPS[i - 1]
            result[cur] = d[cur] / d[prev] * 100 if d[prev] else None
        return result

    def e2e_rate(self):
        """Visits → onboarded conversion rate, or None."""
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
            self.range_str = f"{lo_s} – {hi_s}" if lo_s != hi_s else lo_s
        else:
            self.range_str = "no data"


class FlowchartNodes:
    """Nine node/edge counts for the flowchart."""

    def __init__(self, rows: List[Row]):
        onb = [r for r in rows if is_onboarding(r)]
        passed = [r for r in onb if opener_passed(r)]
        asked = [r for r in passed if has_question(r)]

        self.visit = len(onb)
        self.opener_rejection = len(onb) - len(passed)
        self.asked_questions = len(asked)
        self.direct_to_demo = len(passed) - len(asked)
        self.proceeded_to_demo = sum(1 for r in onb if did_demo(r))
        self.asked_q_to_demo = sum(1 for r in asked if did_demo(r))
        self.demo_rejection = self.asked_questions - self.asked_q_to_demo
        self.onboarded = sum(1 for r in onb if did_onboard(r))
        self.not_onboarded = self.proceeded_to_demo - self.onboarded


def ambassador_breakdown(rows: List[Row]) -> List[Tuple[str, FunnelMetrics]]:
    """Per-ambassador funnel metrics, sorted by visits descending."""
    by_amb = defaultdict(list)
    for row in rows:
        by_amb[ambassador_name(row)].append(row)
    result = [(name, FunnelMetrics(amb_rows)) for name, amb_rows in by_amb.items()]
    result.sort(key=lambda x: -x[1].visits)
    return result


class QuestionDropoffData:
    """Pre-computed data for the Question → Demo dropoff card."""

    def __init__(self, rows: List[Row]):
        onb = [r for r in rows if is_onboarding(r)]
        passed = [r for r in onb if opener_passed(r)]
        asked = [r for r in passed if has_question(r)]

        # Section A — overall stats
        self.total_asked = len(asked)
        self.converted_to_demo = sum(1 for r in asked if did_demo(r))
        self.dropped_off = self.total_asked - self.converted_to_demo
        self.conversion_rate: Optional[float] = (
            self.converted_to_demo / self.total_asked * 100
            if self.total_asked else None
        )

        # Section B — individual topic counts from dropoff rows
        dropoff_rows = [r for r in asked if not did_demo(r)]
        all_topics = []
        for r in dropoff_rows:
            all_topics.extend(split_questions(r))
        q_counts = Counter(all_topics)
        self.dropoff_questions: List[Tuple[str, int]] = (
            q_counts.most_common(MAX_DROPOFF_QUESTIONS)
        )

        # Section C — per-ambassador Q→Demo stats
        by_amb: dict[str, list] = defaultdict(list)
        for r in asked:
            by_amb[ambassador_name(r)].append(r)

        amb_stats: List[Tuple[str, int, int, int, Optional[float], List[Tuple[str, int]]]] = []
        for name, amb_rows in by_amb.items():
            n_asked = len(amb_rows)
            n_demos = sum(1 for r in amb_rows if did_demo(r))
            n_drops = n_asked - n_demos
            rate = n_demos / n_asked * 100 if n_asked else None
            amb_topics = []
            for r in amb_rows:
                amb_topics.extend(split_questions(r))
            top_qs = Counter(amb_topics).most_common(3)
            amb_stats.append((name, n_asked, n_demos, n_drops, rate, top_qs))

        # Sort ascending by conv rate (worst first), None last
        amb_stats.sort(key=lambda x: x[4] if x[4] is not None else 999)
        self.ambassador_stats = amb_stats
