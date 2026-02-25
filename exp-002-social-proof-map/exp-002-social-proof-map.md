# EXP-002: Social Proof Map

**STATUS: ANALYZING** — Phase 2 data collection in progress; testing whether showing a map of nearby ZAR merchants at the opener improves E2E onboarding rate from 7.5% to 15%+.

---

## Scorecard

| Metric | Baseline | Current | Target |
|--------|----------|---------|--------|
| E2E onboarding rate (visits → QR setup done) | 7.5% (control, Feb 11–15, n=268) | — (Phase 2 ongoing) | 15%+ |
| Opener pass rate | 55.6% (control) | — | 75%+ |
| Sample — treatment visits | Phase 1: 51 (Sharoon only) | Phase 2: 100+ target (3 ambassadors) | — |

## Hypothesis

IF ambassadors show a map of nearby ZAR merchants during the opener THEN opener pass rate increases by 20+pp and E2E onboarding rate doubles BECAUSE visual social proof resolves the trust objection ("is this real?") faster than verbal claims.

## Success Criteria

- **Validated if:** E2E ≥ 15% AND effect consistent across 2+ ambassadors → SHIP IT — build merchant map in app, retrain all ambassadors
- **Invalidated if:** No E2E improvement or regression → KILL IT — map adds friction without credibility benefit
- **Inconclusive if:** E2E directional improvement but < 15%, or only 1 ambassador shows effect → ITERATE; or insufficient Phase 2 data (< 50 treatment visits) → EXTEND

**Confirmation metric rule**: If E2E improves but opener pass rate doesn't, the result is suspect — classify as ITERATE at best.

**Ambassador heterogeneity rule**: If > 50% of effect variance is between-ambassador, the map effect is not transferable — classify as ITERATE and investigate what Sharoon does differently.

## The Experiment

Phase 1 data showed Sharoon's opener pass rate at 96.1% vs 55.6% control (+40.5pp). While E2E improvement was modest (9.8% vs 7.5%), the opener signal was strong enough to warrant Phase 2 expansion to Afsar and Arslan — testing whether the effect is method-driven or Sharoon-specific. Decision authority: Turab (ship/kill), Qasim (retrains).

## Minimum Viable Test

- **Intervention:** Ambassadors show a map of nearby ZAR merchants during the opener
- **Who:** Treatment ambassadors (Sharoon, Afsar, Arslan); all others are control
- **How:** Person-based split with staggered start dates (Sharoon Feb 11, Afsar/Arslan Feb 16+)
- **Duration:** Phase 1: Feb 11–15 (Sharoon only). Phase 2: Feb 16+ open-ended until 100+ treatment visits
- **Controls:** Same Google Sheet form, same visit areas, same time period (concurrent split)

### Split Design

| Ambassador | Role | Start Date |
|------------|------|------------|
| Sharoon Javed | Treatment (map) | Feb 11 |
| Afsar Khan | Treatment (map) | Feb 16 |
| Arslan Ansari | Treatment (map) | Feb 16 |
| All others | Control (no map) | — |

**Split logic**: A row is treatment if the ambassador is in the map group AND the row date >= their start date. Afsar/Arslan's pre-Feb 16 data serves as control (their own baseline), enabling before/after comparison per ambassador.

### Phase Design

- **Phase 1** (Feb 11–15): Sharoon only. Tests whether the map works for one ambassador.
- **Phase 2** (Feb 16+): Sharoon + Afsar + Arslan. Tests whether the map effect is method-driven or person-driven.

## Results

### What happened

Phase 2 data collection in progress.

Phase 1 (Sharoon only, Feb 11–15): Opener pass rate 96.1% vs 55.6% control (+40.5pp). E2E: 9.8% vs 7.5% (directional). Demo conversion for Sharoon: 18.4% vs 46.3% control — the map gets merchants past the opener but they may not be progressing to demos at the same rate.

### What we learned

*Pending Phase 2 completion.*

### What we'd do differently

*Pending Phase 2 completion.*

**Decision:** —
**Decision notes:** —

## What Happens Next

**Key question for Phase 2:** Sharoon's demo conversion was low (18.4% vs 46.3% control). Phase 2 will reveal whether this is a Sharoon-specific behavior or a map-induced pattern (merchants who engage via social proof may need a different demo transition).

- **Next experiment:** Determined by Phase 2 outcome and decision rule
- **Assumption update:** Pending
- **Implementation:** Turab decides, Qasim retrains if SHIP

## Detail

### Raw Data

Google Sheet visit form — concurrent control/treatment split.

### Methodology

**Statistical Validity:**

| Check | Assessment |
|-------|-----------|
| Sample size per variant | Phase 1: 51 treatment / 268 control — WEAK. Phase 2 target: 100+ treatment |
| MDE | At 80% power, 95% CI: MDE ~15pp for E2E (current n). Phase 2 will reduce to ~10pp |
| Power/confidence | WEAK for Phase 1 alone. Phase 2 expansion is specifically designed to address this |
| Randomization | Person-based, not random assignment. Ambassador skill is a confounder |
| Duration | Phase 1: 5 days. Phase 2: open-ended until sufficient sample |

**Verdict**: WEAK — prefix all Phase 1 claims with "Directional:". Phase 2 data required before any SHIP decision.

**Prior experiments:**

| EXP | What we learned | How it informs this experiment |
|-----|----------------|-------------------------------|
| EXP-001 | Demo-first opener increased demo rate from 7% to 48%, but mid-funnel bottleneck persists: 73% of question-askers never see a demo | Social proof map targets the same bottleneck from a different angle — reduce questions by building trust upfront |
| EXP-006 | Universal redirect phrase for Q→Demo improved conversion | Complementary intervention — redirect handles questions that do arise, map prevents them from arising |

### Per-Ambassador Breakdown

See Split Design table above. Afsar and Arslan's pre-Feb 16 data serves as their own baseline for before/after comparison.

### Gate Log

| Date | From | To | Rationale | By |
|------|------|-----|-----------|-----|
| | | | | |

**Kill criteria:**

| Check | Trigger | Authority |
|-------|---------|-----------|
| Phase 2 mid-point (Feb 19) | E2E below 10% for map group AND no ambassador improvement | Turab can kill |
| Cost ceiling | N/A (no financial cost — map is free to show) | — |
| Contamination | Control ambassadors start showing the map | Qasim flags, Turab decides |
