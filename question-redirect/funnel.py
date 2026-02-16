"""Pure computation — Q→Demo sub-funnel metrics."""

from collections import Counter, defaultdict
from datetime import date
from typing import Dict, List, Optional, Tuple

from data import (
    Row, row_date, is_onboarding, opener_passed, has_question,
    did_demo, ambassador_name, split_questions,
)
from config import MAX_DROPOFF_QUESTIONS


class QDemoMetrics:
    """Q→Demo conversion metrics for a set of rows."""

    def __init__(self, rows: List[Row]):
        onb = [r for r in rows if is_onboarding(r)]
        passed = [r for r in onb if opener_passed(r)]
        asked = [r for r in passed if has_question(r)]

        self.visits = len(onb)
        self.opener_passed = len(passed)
        self.questions_asked = len(asked)
        self.converted_to_demo = sum(1 for r in asked if did_demo(r))
        self.dropped_off = self.questions_asked - self.converted_to_demo
        self.q_demo_rate: Optional[float] = (
            self.converted_to_demo / self.questions_asked * 100
            if self.questions_asked else None
        )

        # Topic breakdown — all questions from those who asked
        all_topics: List[str] = []
        for r in asked:
            all_topics.extend(split_questions(r))
        self.topic_counts = Counter(all_topics)

        # Dropoff topic breakdown
        dropoff_rows = [r for r in asked if not did_demo(r)]
        dropoff_topics: List[str] = []
        for r in dropoff_rows:
            dropoff_topics.extend(split_questions(r))
        self.dropoff_topic_counts = Counter(dropoff_topics)
        self.top_dropoff: List[Tuple[str, int]] = (
            self.dropoff_topic_counts.most_common(MAX_DROPOFF_QUESTIONS)
        )


class TopicConversion:
    """Per-topic Q→Demo conversion rates."""

    def __init__(self, rows: List[Row]):
        onb = [r for r in rows if is_onboarding(r)]
        passed = [r for r in onb if opener_passed(r)]
        asked = [r for r in passed if has_question(r)]

        # For each topic: how many asked, how many converted
        topic_asked: Dict[str, int] = Counter()
        topic_demo: Dict[str, int] = Counter()

        for r in asked:
            topics = split_questions(r)
            demoed = did_demo(r)
            for t in topics:
                topic_asked[t] += 1
                if demoed:
                    topic_demo[t] += 1

        self.topics: List[Tuple[str, int, int, Optional[float]]] = []
        for topic, asked_count in topic_asked.most_common():
            demo_count = topic_demo.get(topic, 0)
            rate = demo_count / asked_count * 100 if asked_count else None
            self.topics.append((topic, asked_count, demo_count, rate))


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


def ambassador_q_demo(rows: List[Row]) -> List[Tuple[str, QDemoMetrics]]:
    """Per-ambassador Q→Demo metrics, sorted by Q→Demo rate ascending (worst first)."""
    by_amb: Dict[str, List[Row]] = defaultdict(list)
    for row in rows:
        by_amb[ambassador_name(row)].append(row)

    result = [(name, QDemoMetrics(amb_rows)) for name, amb_rows in by_amb.items()]
    result.sort(key=lambda x: x[1].q_demo_rate if x[1].q_demo_rate is not None else 999)
    return result
