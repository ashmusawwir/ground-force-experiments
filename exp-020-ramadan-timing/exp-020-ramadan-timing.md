# EXP-020: Ramadan Visit Timing Optimization

> **One-liner**: "We're testing whether shifting ambassador visits to post-Taraweeh nighttime improves onboarding rates during Ramadan compared to compressed daytime visits."

## Experiment Card

| Element | Detail |
|---------|--------|
| Research Question | During Ramadan, what are the actual productive windows, and does post-Taraweeh nighttime outperform compressed daytime? |
| Decision This Informs | Whether to formalize a nighttime visit schedule for Ramadan (Qasim, immediate). If nighttime wins, retrain all ambassadors on post-Taraweeh schedule. |
| Primary Metric | Onboardings per ambassador per day (observed via Sheet + DB) |
| Confirmation Metric | E2E rate by time window (daytime vs nighttime) |
| Baseline | Pre-Ramadan: 622 evening visits at 8% onboard rate; 489 daytime visits at 4% |
| Target | Identify which Ramadan window produces onboarding rates >= pre-Ramadan evening baseline (8%) |
| Sample Size | Observational — all ambassadors, all visits during Phase 1 |
| Controls | Natural quasi-experiment: city (Karachi vs Lahore Iftar difference), window (day vs night) |
| Duration | Phase 1: Feb 19–24 (observation); Phase 2: Day 6+ (schedule optimization) |

## Decision Rules

| Result | Action |
|--------|--------|
| Post-Taraweeh visits convert >= pre-Ramadan evening rates (8%) | **SHIP IT** — formalize nighttime schedule for all ambassadors |
| Daytime-only ambassadors match or beat nighttime ones | **SHIP IT** — optimize daytime window (12:30–3pm concentration) |
| Both windows significantly worse than pre-Ramadan | **ACCEPT** — Ramadan productivity dip is structural, don't over-optimize |
| Ambassadors naturally split (some day, some night) | **ITERATE** — test full-team shift to winning window in Phase 2 |

## Kill Criteria

| Check | Trigger | Authority |
|-------|---------|-----------|
| Phase 1 complete (Day 5) | Zero post-Taraweeh visits across all ambassadors | Turab — abandon nighttime hypothesis |
| Data quality | >30% of visits batch-logged | Qasim — retrain on immediate logging |
| Cumulative fatigue | Week 3 onboardings/day < 50% of Week 1 | Turab — adjust expectations |

## Context

### Prior experiments
| EXP | What we learned | How it informs this experiment |
|-----|----------------|-------------------------------|
| EXP-001 | Demo-first opener lifts E2E from 4% to ~7% | Baseline conversion rates for timing analysis |
| EXP-006 | Redirect phrase improves Q->Demo transition | Ambassador technique is a confound we control for |

### What prompted this
Pre-Ramadan data shows evening visits (5pm+) convert at 2x the daytime rate (8% vs 4% E2E, n=1,111). Ramadan eliminates the 5-9:30pm window due to Iftar/Taraweeh. The question is whether post-Taraweeh (9:30pm-midnight) can replace the lost productive window.

## Metrics

| Metric | Source | Role |
|--------|--------|------|
| Onboardings per ambassador per day | Sheet + DB | **ARBITER** |
| Visits per ambassador per day | Sheet | Capacity diagnostic (NOT a target) |
| E2E rate by time bucket | Sheet + DB | Window quality |
| Daytime vs Nighttime conversion | Sheet | Core comparison |
| Hourly conversion rate | Sheet | Granular timing signal |
| Active window (first -> last visit) | Sheet timestamps | Schedule tracking |
| Batch-logging flags | Sheet timestamps | Data quality |
| City comparison | Sheet | Natural quasi-experiment |
| Week-over-week trend | Sheet | Cumulative fatigue |
