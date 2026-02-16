# EXP-002: Social Proof Map

> **One-liner**: "We're testing whether showing a map of nearby ZAR merchants at the opener improves end-to-end onboarding rate from 7.5% (control) to 15%+ for the map group."

## Experiment Card

| Element | Detail |
|---------|--------|
| Hypothesis | IF ambassadors show a map of nearby ZAR merchants during the opener THEN opener pass rate increases by 20+pp and E2E onboarding rate doubles BECAUSE visual social proof resolves the trust objection ("is this real?") faster than verbal claims |
| Decision This Informs | Should we build a merchant map feature in the app and retrain all ambassadors on social proof openers? (Turab decides, Qasim retrains) |
| Primary Metric | End-to-end onboarding rate (visits -> QR setup done) — observed |
| Confirmation Metric | Opener pass rate (must also improve; if E2E improves but opener doesn't, something else is driving it) |
| Baseline | 7.5% E2E, 55.6% opener pass (control group, Feb 11-15, n=268) |
| Target | 15% E2E, 75%+ opener pass |
| Sample Size | Phase 1: 51 treatment visits (Sharoon only). Phase 2: targeting 100+ treatment visits (3 ambassadors) |
| Controls | Same Google Sheet form, same visit areas, same time period (concurrent split) |
| Duration | Phase 1: Feb 11-15 (Sharoon only) -> Phase 2: Feb 16+ (Sharoon + Afsar + Arslan) |

## Design

### Split Type: Person-based with staggered start dates

| Ambassador | Role | Start Date |
|------------|------|------------|
| Sharoon Javed | Treatment (map) | Feb 11 |
| Afsar Khan | Treatment (map) | Feb 16 |
| Arslan Ansari | Treatment (map) | Feb 16 |
| All others | Control (no map) | - |

**Split logic**: A row is treatment if the ambassador is in the map group AND the row date >= their start date. Otherwise control. This means Afsar/Arslan's pre-Feb 16 data serves as control (their own baseline), enabling before/after comparison per ambassador.

### Phase Design

- **Phase 1** (Feb 11-15): Sharoon only. Tests whether the map works for one ambassador.
- **Phase 2** (Feb 16+): Sharoon + Afsar + Arslan. Tests whether the map effect is method-driven (transfers across ambassadors) or person-driven (Sharoon-specific).

## Decision Rules

| Result | Action |
|--------|--------|
| E2E >= 15% AND effect consistent across 2+ ambassadors | SHIP IT — build merchant map in app, retrain all ambassadors |
| E2E directional improvement but < 15%, or only 1 ambassador shows effect | ITERATE — verbal social proof training for all, no app feature yet |
| No E2E improvement or regression | KILL IT — map adds friction without credibility benefit |
| Insufficient Phase 2 data (< 50 treatment visits) | EXTEND — wait for more data before deciding |

**Confirmation metric rule**: if E2E improves but opener pass rate doesn't, the result is suspect — classify as ITERATE at best.

**Ambassador heterogeneity rule**: if > 50% of effect variance is between-ambassador (e.g., only Sharoon shows improvement), the map effect is not transferable — classify as ITERATE and investigate what Sharoon does differently.

## Kill Criteria

| Check | Trigger | Authority |
|-------|---------|-----------|
| Phase 2 mid-point (Feb 19) | E2E below 10% for map group AND no ambassador improvement | Turab can kill |
| Cost ceiling | N/A (no financial cost — map is free to show) | - |
| Contamination | Control ambassadors start showing the map | Qasim flags, Turab decides |

## Statistical Validity

| Check | Assessment |
|-------|-----------|
| Sample size per variant | Phase 1: 51 treatment / 268 control — WEAK. Phase 2 target: 100+ treatment |
| MDE | At 80% power, 95% CI: MDE ~15pp for E2E (current n). Phase 2 will reduce to ~10pp |
| Power/confidence | WEAK for Phase 1 alone. Phase 2 expansion is specifically designed to address this |
| Randomization | Person-based, not random assignment. Ambassador skill is a confounder |
| Duration | Phase 1: 5 days. Phase 2: open-ended until sufficient sample |

**Verdict**: WEAK — prefix all Phase 1 claims with "Directional:". Phase 2 data required before any SHIP decision.

## Context

### Prior experiments

| EXP | What we learned | How it informs this experiment |
|-----|----------------|-------------------------------|
| EXP-001 | Demo-first opener increased demo rate from 7% to 48%, but mid-funnel bottleneck persists: 73% of question-askers never see a demo | Social proof map targets the same bottleneck from a different angle — reduce questions by building trust upfront |
| EXP-006 | Universal redirect phrase for Q->Demo improved conversion | Complementary intervention — redirect handles questions that do arise, map prevents them from arising |

### What prompted this

Phase 1 data showed Sharoon's opener pass rate at 96.1% vs 55.6% control (+40.5pp). While E2E improvement was modest (9.8% vs 7.5%), the opener signal was strong enough to warrant expansion. Adding Afsar and Arslan tests whether this is the map or just Sharoon.

### Key question for Phase 2

Sharoon's demo conversion was low (18.4% vs 46.3% control). The map gets merchants past the opener but they may not be progressing to demos at the same rate. Phase 2 will reveal whether this is a Sharoon-specific behavior or a map-induced pattern (merchants who engage via social proof may need a different demo transition).
