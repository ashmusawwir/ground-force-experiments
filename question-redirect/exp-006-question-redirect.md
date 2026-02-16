# EXP-006: Question Redirect Protocol

> **One-liner**: "We're testing whether training ambassadors to redirect merchant questions into immediate demos improves Q→Demo rate from 27% to ≥45%."

## Experiment Card

| Element | Detail |
|---------|--------|
| Hypothesis | IF ambassadors are trained to redirect merchant questions into immediate app demos THEN Q→Demo rate increases from 25% to ≥45% BECAUSE merchant questions are buying signals best answered by showing the product, not explaining it verbally — and a trained redirect removes the ambassador's hesitation about when to transition |
| Decision This Informs | Should we make "redirect to demo" the standard trained response to all merchant questions? **Qasim** retrains all ambassadors on the technique; **Daniel** builds the redirect flow into the automated in-app playbook |
| Primary Metric | Q→Demo rate (reported, visit form) — proportion of question-asking merchants who proceed to a live demo |
| Confirmation Metric | E2E onboarding rate (visits → onboarded). If Q→Demo improves but E2E is flat, the result is suspect — we learned this from EXP-001 where opener conversion soared (+51pp) but E2E barely moved |
| Baseline | 25% Q→Demo (43/172 question-askers, Feb 10-15, pre-training period) |
| Target | 50% aspirational. 45% = SHIP threshold (MDE ≈ 18pp at n≈108/group, so 45% is the minimum detectable improvement) |
| Sample Size | 172 pre-training (existing, Feb 10-15), ~150 post-training (target). See Statistical Validity for clustering adjustment |
| Controls | Same Google Sheet form, same visit areas, same ambassador roster. Only change: redirect training intervention |
| Duration | Pre-training: Feb 10 – Feb 15 (6 days) → Post-training: Feb 16 – Feb 22 (7 days) |

## Decision Rules

| Result | Verdict | Action |
|--------|---------|--------|
| ≥4/5 ambassadors individually improve AND pooled Q→Demo ≥45% | **SHIP IT** | Qasim retrains all ambassadors on redirect technique. Daniel builds redirect flow into automated in-app playbook. Roll out within 1 week |
| Pooled Q→Demo 35-44%, OR improvement driven by only 1-2 ambassadors | **ITERATE** | Identify what top performers do differently. Redesign training with per-ambassador coaching. Re-run with compliance tracking |
| Pooled Q→Demo <35%, OR most ambassadors flat/regressing | **KILL IT** | The Q→Demo bottleneck isn't about transition timing — investigate whether the problem is demo skill, merchant objection type, or product-market fit |
| <50 post-training question-askers by Feb 22 | **EXTEND** | Extend to Feb 28. If still insufficient, the volume problem is itself a finding |

**Confirmation metric rule**: If Q→Demo improves but E2E onboarding rate is flat or declining, classify as ITERATE at best. A faster path to demo is worthless if demos don't convert to onboardings.

## Kill Criteria

| Check | Trigger | Authority |
|-------|---------|-----------|
| Mid-point (Feb 19, day 4) | Pooled Q→Demo below 30% with n≥40 post-training | Turab can kill early |
| Confirmation metric | E2E flat after 5 days of Q→Demo improvement | Asharib flags, Turab decides |
| Ambassador compliance | ≥3 ambassadors show no individual improvement | Qasim escalates to Turab |
| Volume | <8 question-askers/day post-training (vs ~32/day baseline) | Asharib flags — indicates form compliance or visit volume issue |

## Statistical Validity

| Check | Answer |
|-------|--------|
| Sample size per variant | 172 pre (existing, Feb 10-15), ~150 post (target). Naive: 108/group sufficient — we exceed this pre-training. Cluster-adjusted: 416/group ideal but infeasible |
| MDE | 20pp (25% → 45%) at 80% power, α=0.05, naive two-proportion z-test |
| Power / Confidence | 80% power, 95% confidence — but this assumes independent observations, which is violated by ambassador clustering |
| Randomization | None. Training-based split (pre vs post). Same ambassadors in both periods. No true control group |
| Duration covers full cycle? | 7 days post-training covers one full work week. Does not cover weekend effects or merchant revisits |

### The Clustering Problem

With only **5 active ambassadors**, observations are not independent. Two visits from the same ambassador are more correlated than visits from different ambassadors.

- **Ambassador ICC** (estimated from EXP-001): ~0.15
- **Design effect**: 1 + (20-1) × 0.15 = 3.85
- **Effective sample size**: Reduced by ~4x
- **Ambassador Q→Demo range**: 14% to 54% — a 40pp spread, larger than the 18pp effect we're trying to detect

**No duration fixes this.** The fundamental constraint is 5 clusters (ambassadors), not visit volume.

### Mitigation: Ambassador-Stratified Analysis

Instead of pooling all visits:
1. Compute each ambassador's individual pre vs post Q→Demo rate
2. Weight each ambassador equally (prevents one prolific ambassador from driving the result)
3. Exclude ambassadors with <10 questions in either period (insufficient individual data)
4. Check temporal stability — if the effect is driven by one anomalous day, it's not real

**Validity verdict: WEAK**

All claims must be prefixed with "Directional:". The experiment can produce a useful signal — not a statistically rigorous conclusion. What would make it SUFFICIENT: 10+ ambassadors or a person-based split (train some, not others).

## Assumption Check

**1. What has to be true for this to work?**
- Ambassadors must actually use the redirect phrase (unverifiable — no form field tracks this)
- The Q→Demo bottleneck must be about transition timing, not demo skill or merchant objection severity
- Questions must genuinely be answerable by showing the app (true for top 5 question types: Company Info, How It Works, Trust & Safety, Legal & FIA, Withdrawals)

**2. What's the riskiest assumption?**
That ambassadors will consistently use the redirect after training. Field compliance is historically variable. The Hawthorne effect (performing better because they know they're being watched post-training) is a real confound.

**3. How can we test it cheaply?**
We can't isolate the phrase — but we can check if the gap between "asked questions" and "got demo" closes. If it does, *something* about the training worked, even if we can't attribute it solely to the redirect phrase.

**4. Does this create perverse incentives?**
Low risk. The redirect phrase costs nothing to sustain. There's no payment tied to demo count. Minor risk: ambassadors might rush to demo before the merchant is ready, reducing demo quality — monitor onboarding rate as a check.

**5. Does it require ambassador skill?**
Yes, moderately. Using a redirect phrase is simple, but knowing *when* to use it (vs. when a merchant needs a direct answer first) requires judgment. Expect high variance between ambassadors. This is why we use ambassador-stratified analysis.

## Context

### Prior experiments

| EXP | What we learned | How it informs this experiment |
|-----|----------------|-------------------------------|
| EXP-001 | Demo-first opener improved opener pass-through from 10% to 61% (+51pp), but mid-funnel collapsed. Q→Demo rate was only 25% (43/172, full pre-training period Feb 10-15). E2E barely moved (5.4% → 5.8%). The Q&A stage is the single biggest funnel leak | Identified the Q→Demo bottleneck. Top question topics (Company Info, How It Works, Trust & Safety) are all better shown than explained — motivating the redirect approach |
| EXP-001 (per-ambassador, Feb 10-15) | Arslan Ansari hit 35% Q→Demo (6/17, Directional), Junaid Ahmed 32% (9/28, Reliable). Zahid at 10% (4/40, Reliable), Sharoon at 17% (9/53, Reliable). Massive between-ambassador variance: 10% to 100% | The gap between worst (10%) and best performers suggests room for a trained method to close it. But the variance also means individual ambassador skill matters — the redirect phrase alone may not be enough for low performers |

### What prompted this

EXP-001's Q→Demo analysis revealed that **75% of question-asking merchants never see a demo** (129/172 dropped off, Feb 10-15). The top dropoff questions — Company Info, How It Works, Trust & Safety — are all product questions that a live demo answers more convincingly than a verbal explanation. Ambassadors were getting stuck in verbal Q&A loops instead of transitioning to the app. Generic redirect guidance was given when EXP-001 results first surfaced; rigorous, directed training starts Feb 16.

### Falsifiability

This hypothesis is disproved if:
- Q→Demo rate stays below 35% after 7 days of post-training data (≥100 question-askers)
- OR Q→Demo improves but is driven by 1-2 ambassadors (not the method — just better individuals)
- OR Q→Demo improves but E2E onboarding rate doesn't follow (the demo transition was premature, not helpful)

## Pre-Training Baseline Snapshot (Feb 10-15, 6 days)

Captured at experiment start for reference:

| Metric | Value |
|--------|-------|
| Total visits | 363 |
| Opener passed | 223 (61%) |
| Questions asked | 172 (77% of opener passed) |
| Converted to demo | 43 (25% Q→Demo) |
| Dropoff | 129 (75% of question-askers) |

### Per-Ambassador Pre-Training Q→Demo

| Ambassador | Qs Asked | Demos | Q→Demo | Tier |
|---|---|---|---|---|
| Muhammad Zahid | 40 | 4 | 10.0% | Reliable |
| Sharoon Javed | 53 | 9 | 17.0% | Reliable |
| Afsar Khan | 23 | 5 | 21.7% | Reliable |
| Junaid Ahmed | 28 | 9 | 32.1% | Reliable |
| Arslan Ansari | 17 | 6 | 35.3% | Directional |
| Muhammad Irfan | 6 | 5 | 83.3% | Directional |
| Owais Feroz | 5 | 5 | 100.0% | Insufficient |
