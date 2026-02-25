# EXP-006: Question Redirect Protocol

**STATUS: ANALYZING** — Post-training data collection complete (Feb 10–22); measuring whether training ambassadors to redirect questions into demos improved Q→Demo rate from 25% to ≥45%.

---

## Scorecard

| Metric | Baseline | Current | Target |
|--------|----------|---------|--------|
| Q→Demo rate (reported) | 25% (43/172 question-askers, Feb 10–15) | — | 45% (SHIP threshold) / 50% (aspirational) |
| E2E onboarding rate | ~5.8% (pre-training) | — | Parallel improvement required |
| Sample | 172 pre-training (Feb 10–15), ~150 post-training target (Feb 16–22) | — | — |

## Hypothesis

IF ambassadors are trained to redirect merchant questions into immediate app demos THEN Q→Demo rate increases from 25% to ≥45% BECAUSE merchant questions are buying signals best answered by showing the product, not explaining it verbally — and a trained redirect removes the ambassador's hesitation about when to transition.

## Success Criteria

- **Validated if:** ≥4/5 ambassadors individually improve AND pooled Q→Demo ≥45% → SHIP IT — Qasim retrains all ambassadors, Daniel builds redirect flow into automated playbook
- **Invalidated if:** Pooled Q→Demo <35%, OR most ambassadors flat/regressing → KILL IT — investigate whether bottleneck is demo skill, merchant objection type, or product-market fit
- **Inconclusive if:** Pooled Q→Demo 35–44%, OR improvement driven by only 1–2 ambassadors → ITERATE; or <50 post-training question-askers by Feb 22 → EXTEND to Feb 28

**Confirmation metric rule**: If Q→Demo improves but E2E is flat or declining, classify as ITERATE at best. A faster path to demo is worthless if demos don't convert to onboardings.

## The Experiment

EXP-001's Q→Demo analysis revealed 75% of question-asking merchants never see a demo (129/172 dropped off, Feb 10–15). Top dropoff questions — Company Info, How It Works, Trust & Safety — are all better shown than explained. Ambassadors were stuck in verbal Q&A loops instead of transitioning to the app. Rigorous, directed redirect training started Feb 16; this experiment measures the before/after effect.

## Minimum Viable Test

- **Intervention:** Redirect training — ambassadors trained on a phrase to transition merchant questions into immediate app demos
- **Who:** All active ambassadors (5), same roster pre and post
- **How:** Training-based before/after split (pre: Feb 10–15, post: Feb 16–22). No true control group.
- **Duration:** Pre-training: 6 days. Post-training: 7 days (one full work week).
- **Controls:** Same form, same visit areas, same ambassador roster. Only change: redirect training.

## Results

### What happened

*Post-training analysis pending.*

**Pre-training baseline (Feb 10–15, 6 days):**

| Metric | Value |
|--------|-------|
| Total visits | 363 |
| Opener passed | 223 (61%) |
| Questions asked | 172 (77% of opener passed) |
| Converted to demo | 43 (25% Q→Demo) |
| Dropoff | 129 (75% of question-askers) |

**Per-ambassador pre-training Q→Demo:**

| Ambassador | Qs Asked | Demos | Q→Demo | Tier |
|---|---|---|---|---|
| Muhammad Zahid | 40 | 4 | 10.0% | Reliable |
| Sharoon Javed | 53 | 9 | 17.0% | Reliable |
| Afsar Khan | 23 | 5 | 21.7% | Reliable |
| Junaid Ahmed | 28 | 9 | 32.1% | Reliable |
| Arslan Ansari | 17 | 6 | 35.3% | Directional |
| Muhammad Irfan | 6 | 5 | 83.3% | Directional |
| Owais Feroz | 5 | 5 | 100.0% | Insufficient |

### What we learned

*Pending post-training analysis.*

### What we'd do differently

*Pending.*

**Decision:** —
**Decision notes:** —

## What Happens Next

- **Next experiment:** Determined by post-training result and decision rule
- **Assumption update:** Pending
- **Implementation:** Qasim retrains all if SHIP; Daniel builds redirect flow into playbook

## Detail

### Raw Data

Google Sheet visit form — pre-training (Feb 10–15) and post-training (Feb 16–22) periods.

### Methodology

**The Clustering Problem:**

With only 5 active ambassadors, observations are not independent. Two visits from the same ambassador are more correlated than visits from different ambassadors.

- **Ambassador ICC** (estimated from EXP-001): ~0.15
- **Design effect**: 1 + (20-1) × 0.15 = 3.85
- **Effective sample size**: Reduced by ~4x
- **Ambassador Q→Demo range**: 14% to 54% — a 40pp spread, larger than the 18pp effect we're trying to detect

No duration fixes this. The fundamental constraint is 5 clusters (ambassadors), not visit volume.

**Mitigation — Ambassador-Stratified Analysis:**

Instead of pooling all visits:
1. Compute each ambassador's individual pre vs post Q→Demo rate
2. Weight each ambassador equally (prevents one prolific ambassador from driving the result)
3. Exclude ambassadors with <10 questions in either period
4. Check temporal stability — if the effect is driven by one anomalous day, it's not real

**Statistical validity:**

| Check | Answer |
|-------|--------|
| Sample size per variant | 172 pre (existing, Feb 10–15), ~150 post (target). Naive: 108/group sufficient. Cluster-adjusted: 416/group ideal but infeasible |
| MDE | 20pp (25% → 45%) at 80% power, α=0.05, naive two-proportion z-test |
| Power / Confidence | 80% power, 95% confidence — but this assumes independent observations, violated by ambassador clustering |
| Randomization | None. Training-based split (pre vs post). No true control group |
| Duration covers full cycle? | 7 days post-training covers one full work week |

**Validity verdict: WEAK** — all claims must be prefixed with "Directional:".

**Assumption check:**

1. **What has to be true?** Ambassadors must actually use the redirect phrase. The Q→Demo bottleneck must be about transition timing, not demo skill. Questions must be answerable by showing the app (true for top 5 question types: Company Info, How It Works, Trust & Safety, Legal & FIA, Withdrawals).
2. **Riskiest assumption?** Field compliance. Hawthorne effect (performing better post-training because they know they're being watched) is a real confound.
3. **Cheap test?** Check if the gap between "asked questions" and "got demo" closes.
4. **Perverse incentives?** Low risk — no payment tied to demo count. Minor risk: ambassadors might rush to demo before merchant is ready.
5. **Ambassador skill?** Yes, moderately. Knowing *when* to redirect requires judgment. Expect high variance between ambassadors.

**Falsifiability**: Disproved if Q→Demo stays below 35% after 7 days of post-training data (≥100 question-askers); OR if Q→Demo improves but driven by 1–2 ambassadors; OR if Q→Demo improves but E2E onboarding rate doesn't follow.

**Prior experiments:**

| EXP | What we learned | How it informs this experiment |
|-----|----------------|-------------------------------|
| EXP-001 | Demo-first opener improved opener pass-through from 10% to 61% (+51pp), but mid-funnel collapsed. Q→Demo rate was only 25% (43/172, full pre-training period Feb 10–15). E2E barely moved (5.4% → 5.8%). The Q&A stage is the single biggest funnel leak | Identified the Q→Demo bottleneck. Top question topics are all better shown than explained — motivating the redirect approach |
| EXP-001 (per-ambassador, Feb 10–15) | Arslan 35%, Junaid 32%, Zahid 10%, Sharoon 17%. Massive between-ambassador variance: 10% to 100% | The gap between worst and best performers suggests room for a trained method to close it. But the variance also means individual ambassador skill matters |

### Per-Ambassador Breakdown

See pre-training table in Results. Post-training breakdown pending.

### Gate Log

| Date | From | To | Rationale | By |
|------|------|-----|-----------|-----|
| | | | | |

**Kill criteria:**

| Check | Trigger | Authority |
|-------|---------|-----------|
| Mid-point (Feb 19, day 4) | Pooled Q→Demo below 30% with n≥40 post-training | Turab can kill early |
| Confirmation metric | E2E flat after 5 days of Q→Demo improvement | Asharib flags, Turab decides |
| Ambassador compliance | ≥3 ambassadors show no individual improvement | Qasim escalates to Turab |
| Volume | <8 question-askers/day post-training (vs ~32/day baseline) | Asharib flags |
