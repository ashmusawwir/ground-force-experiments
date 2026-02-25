# EXP-020: Ramadan Visit Timing Optimization

**STATUS: RUNNING** — Testing whether post-Taraweeh nighttime visits improve onboarding rates vs. compressed daytime visits during Ramadan (Phase 1: Feb 19–24 observation, Phase 2: schedule optimization).

---

## Scorecard

| Metric | Baseline | Current | Target |
|--------|----------|---------|--------|
| Onboardings per ambassador per day | Pre-Ramadan evening: 8% E2E (622 visits); daytime: 4% (489 visits) | — | Identify window ≥ pre-Ramadan evening baseline (8%) |
| E2E rate by time window (daytime vs nighttime) | Daytime: 4%, Evening: 8% (pre-Ramadan) | — | Post-Taraweeh ≥ 8% |
| Sample | All ambassadors, all visits during Phase 1 (observational) | — | — |

## Hypothesis

During Ramadan, post-Taraweeh nighttime visits (9:30pm–midnight) can replace the lost productive evening window (5–9:30pm), achieving onboarding rates comparable to or better than the pre-Ramadan evening baseline (8%).

## Success Criteria

- **Validated (nighttime):** Post-Taraweeh visits convert ≥ pre-Ramadan evening rates (8%) → SHIP IT — formalize nighttime schedule for all ambassadors
- **Validated (daytime):** Daytime-only ambassadors match or beat nighttime → SHIP IT — optimize daytime window (12:30–3pm concentration)
- **Inconclusive:** Both windows significantly worse than pre-Ramadan → ACCEPT — Ramadan productivity dip is structural, don't over-optimize
- **Iterate:** Ambassadors naturally split (some day, some night) → test full-team shift to winning window in Phase 2

## The Experiment

Pre-Ramadan data shows evening visits (5pm+) convert at 2× the daytime rate (8% vs 4% E2E, n=1,111). Ramadan eliminates the 5–9:30pm window due to Iftar/Taraweeh. The question is whether post-Taraweeh (9:30pm–midnight) can replace the lost productive window. Natural quasi-experiment: city comparison (Karachi vs Lahore Iftar difference) and window comparison (daytime vs nighttime).

## Minimum Viable Test

- **Intervention:** None — observational. All ambassadors, all visits. Natural behavior tracked.
- **Who:** All ambassadors across Karachi and Lahore
- **How:** City-aware time bucketing (Karachi vs Lahore Iftar/Taraweeh times); window classification (daytime/evening/nighttime)
- **Duration:** Phase 1: Feb 19–24 (observation). Phase 2: Day 6+ (schedule optimization based on Phase 1 findings).
- **Controls:** City comparison (natural quasi-experiment), pre-Ramadan baseline for before/after

## Results

### What happened

*Phase 1 data collection in progress (Feb 19–24).*

### What we learned

*Pending Phase 1 completion.*

### What we'd do differently

*Pending.*

**Decision:** —
**Decision notes:** —

## What Happens Next

- **Phase 2:** If Phase 1 identifies a winning window, shift all ambassadors to that window and measure improvement
- **Decision authority:** Qasim (immediate schedule change), Turab (formal protocol)
- **Assumption update:** Pending Phase 1 completion

## Detail

### Raw Data

Google Sheet visit form — all ambassadors, all Ramadan visits. City tag from "tagging" tab.

### Methodology

**Metrics:**

| Metric | Source | Role |
|--------|--------|------|
| Onboardings per ambassador per day | Sheet + DB | **ARBITER** |
| Visits per ambassador per day | Sheet | Capacity diagnostic (NOT a target) |
| E2E rate by time bucket | Sheet + DB | Window quality |
| Daytime vs Nighttime conversion | Sheet | Core comparison |
| Hourly conversion rate | Sheet | Granular timing signal |
| Active window (first → last visit) | Sheet timestamps | Schedule tracking |
| Batch-logging flags | Sheet timestamps | Data quality |
| City comparison | Sheet | Natural quasi-experiment |
| Week-over-week trend | Sheet | Cumulative fatigue |

**Key extensions in code:**
- City-aware time bucketing (Karachi vs Lahore Iftar/Taraweeh times)
- `fetch_tagging()` — reads "tagging" tab for ambassador→city mapping
- `split_by_ramadan()` — pre-Ramadan vs Ramadan period split
- `split_by_window()` — daytime/evening/nighttime classification
- `detect_batch_logging()` — flags 3+ visits within 5 min
- Bayesian P(night > day) comparison — both uninformative and informative priors
- `bayesian_p_with_prior()` — pre-Ramadan data as informative Beta priors (20/489 day, 50/622 evening)
- `bayesian_p_vs_baseline()` — one-sample P(Ramadan night ≥ pre-Ramadan evening 8%)
- `sequential_credibility()` — daily cumulative P trajectory for sequential monitoring
- `credibility_estimate()` — linear extrapolation of days to P > 0.95
- Hourly heatmap (ambassador × hour grid)
- Weekly trend for cumulative fatigue tracking

**Prior experiments:**

| EXP | What we learned | How it informs this experiment |
|-----|----------------|-------------------------------|
| EXP-001 | Demo-first opener lifts E2E from 4% to ~7% | Baseline conversion rates for timing analysis |
| EXP-006 | Redirect phrase improves Q→Demo transition | Ambassador technique is a confound we control for |

### Per-Ambassador Breakdown

Pending Phase 1 completion. City assignments tracked in "tagging" tab.

### Gate Log

| Date | From | To | Rationale | By |
|------|------|-----|-----------|-----|
| | | | | |

**Kill criteria:**

| Check | Trigger | Authority |
|-------|---------|-----------|
| Phase 1 complete (Day 5) | Zero post-Taraweeh visits across all ambassadors | Turab — abandon nighttime hypothesis |
| Data quality | >30% of visits batch-logged | Qasim — retrain on immediate logging |
| Cumulative fatigue | Week 3 onboardings/day < 50% of Week 1 | Turab — adjust expectations |
