# EXP-004: Merchant Activation Incentive (v5)

> **One-liner**: We're testing whether a tiered cash incentive ($2/$3/$5) can push merchant activation from 23% to 40%+ within each merchant's own 14-day window, for merchants onboarded Feb 1–14.

---

## The Offer

**Three independent qualifiers. Each unlocks a separate cash reward.**

| Qualifier | What You Do | You Earn |
|-----------|-------------|----------|
| **Qualifier A — First Sale** | Send your first cash note or complete your first order (≥$1) | **$2** |
| **Qualifier B — Repeat Seller** | Complete 3+ total sales | **$3** |
| **Qualifier C — Volume Seller** | Reach $10+ in total sales volume | **$5** |

All three qualifiers are **independent** — you can earn any combination. Maximum you can earn: **$10** (all three).

Sales = cash notes you send to customers + orders you fulfill. $0.01 sends don't count — that's the onboarding note sent to new customers.

---

## Who Qualifies

Merchants onboarded to ZAR between **February 1–14, 2026** (44 merchants).

Each merchant has **14 days from their own activation date** to hit each level. The last qualifying window (Feb 14 activation) closes **Feb 28**.

---

## What Counts as a "Sale"

| Counts ✅ | Doesn't Count ❌ |
|-----------|------------------|
| Cash note you **send** to a customer (≥$0.02) | Cash notes you **receive** |
| ZCE order you **fulfill** as merchant | ZCE orders you initiate as buyer |
| Any amount ≥$0.02 | Amounts of $0.01 (test/onboarding notes) |

---

## How You Get Paid

- Rewards are paid within 7 days of verification
- ZAR team checks your sales independently — each transaction must be to a real, distinct customer
- Self-sends or round-trips back to yourself don't count

---

## Examples

**Merchant A** sends a $5 cash note to one customer:
> Qualifier A ✅ (first sale) → earns **$2**

**Merchant B** sends 3 cash notes ($2, $3, $1) to 3 different customers:
> Qualifier A ✅ + Qualifier B ✅ (3 sales, $6 total) → earns **$5**

**Merchant C** fulfills 4 ZCE orders totaling $15:
> Qualifier A ✅ + Qualifier B ✅ + Qualifier C ✅ → earns **$10**

---
---

# Internal: Data-Informed Design Rationale

*Everything above is merchant-facing. Everything below is internal.*

---

## Why These Thresholds (The Data)

**Source**: Organic baseline captured Feb 18 (n=49). Current qualified pool: 44 merchants (Feb 1–14, window-corrected) as of Feb 23.

### Organic Baseline (No Incentive)

| Metric | Value |
|--------|-------|
| Total qualifying merchants | 49 |
| Any sales at all | 11 (22%) |
| 3+ sales | 0 (0%) |
| $10+ volume | 2 (4%) |
| $30+ volume | 1 (2%) |
| Median volume (active only) | $2 |
| Median volume (all) | $0 |

### Distribution

| Bucket | Count | % |
|--------|-------|---|
| 0 sales | 38 | 78% |
| 1-2 sales | 11 | 22% |
| 3-5 sales | 0 | 0% |
| 6+ sales | 0 | 0% |

### Volume of Active Merchants (n=11)

```
$0.10, $0.10, $1, $1, $1, $2, $2.10, $3, $3, $16, $105
```

9 of 11 have ≤$3 total. Two $0.10 amounts are likely test transactions. Zero ZCE orders — 100% cash notes.

### Why the Old Target Was Wrong

EXP-004 v4 required **$30 in sales to 3+ customers within 7 days**.

| Requirement | Merchants Who Hit It Organically |
|-------------|---:|
| 3+ customers | **0** (0%) |
| $30+ volume | **1** (2%) |
| Both | **0** (0%) |

The target was ~10x above organic behavior. Nobody could hit it. The experiment was DOA.

---

## Threshold Design

### Level 1: First Sale ($2)

**Why $1 minimum**: The $0.10 transactions in the data are test/demo sends, not real sales. $1 is the floor of genuine commercial activity (mode of active merchants).

**Why $2 reward**: Small enough to be sustainable at scale. Large enough to motivate the 0→1 transition, which is the hardest behavioral shift (78% of merchants never sell at all).

**Expected hit rate**: 22% organic → target **35-45%** with nudges + incentive. The incentive alone won't do it — WhatsApp reminders and ambassador visits are the real mechanism. The $2 is permission to try.

### Level 2: Repeat Seller ($3)

**Why 3 sales**: Zero merchants have ever done 3 sales organically. This is a genuine stretch goal — it tests whether the first-sale behavior can be repeated.

**Why $3 reward**: Larger than Level 1 because the behavior is harder and more valuable. A merchant who sells 3x has crossed from "tried it once" to "understanding the product."

**Expected hit rate**: 0% organic → target **10-15%** with sustained nudging. If we get >15%, it suggests the activation barrier is primarily motivational, not structural.

### Level 3: Volume Seller ($5)

**Why $10 volume**: Only 2 of 49 merchants (4%) have $10+ organic volume. This level proves real commercial intent — not test transactions.

**Why $5 reward**: Highest tier because this is the behavior we actually want at scale. A merchant doing $10+ in sales is generating real economic activity.

**Expected hit rate**: 4% organic → target **8-12%**. If we get >10%, these merchants are candidates for the regular merchant program.

---

## Current Status (as of Feb 23, 2026)

*Window-correct data: pool = merchants onboarded Feb 1–14 only. Sales counted only within each merchant's own 14-day activation window.*

### Tier Summary

| Tier | Qualified | Rate | Committed |
|------|:---------:|:----:|:---------:|
| L1 (any sale ≥$1) | 10/44 | 23% | $20 |
| L2 (3+ sales) | 2/44 | 5% | $6 |
| L3 ($10+ volume) | 2/44 | 5% | $10 |
| **Total** | — | — | **$36** |

### Sales Distribution (within-window counts)

| Bucket | Count | % |
|--------|:-----:|:-:|
| 0 sales | 31 | 70% |
| 1-2 sales | 11 | 25% |
| 3-5 sales | 2 | 5% |
| 6-10 sales | 0 | 0% |
| 10+ sales | 0 | 0% |

### Window Status by Cohort (as of Feb 23)

| Activation Date | Merchants | Window Closes | Days Left | Status |
|:---------------:|:---------:|:-------------:|:---------:|--------|
| Feb 2 | 2 | Feb 16 | 0 | **Closed** |
| Feb 3 | 4 | Feb 17 | 0 | **Closed** |
| Feb 4 | 7 | Feb 18 | 0 | **Closed** |
| Feb 5 | 3 | Feb 19 | 0 | **Closed** |
| Feb 7 | 2 | Feb 21 | 0 | **Closed** |
| Feb 9 | 2 | Feb 23 | 0 | **Closes today** |
| Feb 10 | 3 | Feb 24 | 1 | Open |
| Feb 11 | 2 | Feb 25 | 2 | Open |
| Feb 12 | 5 | Feb 26 | 3 | Open |
| Feb 13 | 9 | Feb 27 | 4 | Open |
| Feb 14 | 5 | Feb 28 | 5 | Open |

**20 merchants' windows closed/closing today. 24 merchants still have 1-5 days left.**

### Notable Merchants

| Merchant | Onboarding | Sales | Volume | Customers | Tiers | Payout |
|----------|:----------:|:-----:|:------:|:---------:|-------|:------:|
| PE merchant (unnamed) | Feb 14 | 4 | $210 | 2 | L1+L2+L3 | $10 |
| PE merchant (unnamed) | Feb 3 | 3 | $4 | 2 | L1+L2 | $5 |
| Taha Communication | Feb 4 | 2 | $16 | 2 | L1+L3 | $7 |
| Al Furqan Photocopy | Feb 11 | 2 | $3 | 2 | L1 | $2 |

**$210 outlier**: The Feb 14 PE merchant now has 4 sales totaling $210 (was 2 sales / $105 on Feb 18), to 2 distinct customers — **no fraud flags**. Appears to be genuine commercial activity. Verify before attributing to the incentive.

### Fraud Status

**0 of 13 active merchants flagged.** All signals clean:

| Flag | Count |
|------|:-----:|
| Self-send | 0 |
| Dust spam (3+ sales < $0.10) | 0 |
| Single-customer concentration | 0 |

---

## Cost Model

| Scenario | L1 (23→40%) | L2 (0→15%) | L3 (5→10%) | Total Cost |
|----------|:-----------:|:----------:|:----------:|:----------:|
| Conservative | 18 × $2 = $36 | 7 × $3 = $21 | 5 × $5 = $25 | **$82** |
| Optimistic | 22 × $2 = $44 | 10 × $3 = $30 | 8 × $5 = $40 | **$114** |
| Maximum (all 44 hit all 3) | 44 × $10 | — | — | **$440** |

**Committed so far**: $36 (L1: $20 + L2: $6 + L3: $10)

**Cost per activated merchant**: ~$3.60 committed / 10 L1 merchants = **$3.60 per L1** so far.

---

## Statistical Validity

| Check | Assessment |
|-------|-----------|
| Pool size | 44 (Feb 1–14, window-correct) — borderline. At 23% current L1 rate, 95% CI is [11%, 35%]. |
| MDE | Can detect ~14pp lift (23% → 37%) at 80% power. Cannot detect smaller effects. |
| Power verdict | **WEAK** — can detect large effects only. Prefix claims with "Directional." |
| Randomization | None — all qualifying merchants receive the offer. No control group. |
| Window bias | 20 merchants' windows are already closed (final results). 24 still open (in-progress). Within-closed-window L1 rate is ~35-40%. |

**What would make it sufficient**: Pool of 80+ merchants or a control arm (withhold incentive from random 25 merchants).

---

## Fraud Safeguards

| Safeguard | How It Works |
|-----------|-------------|
| **$0.01 filter** | Amounts ≤$0.01 excluded — prevents gaming with test transactions |
| **Distinct customer check** | Each sale must be to a different user — no self-sends or cycling |
| **Independent verification** | ZAR team verifies transactions before payout |
| **$10 cap** | Maximum reward per merchant limits downside |
| **Observed data only** | All metrics from system data (CN + ZCE tables), not self-reported |
| **Window enforcement** | Only sales within each merchant's own 14-day window count |

---

## Decision Rules

| Result | Action |
|--------|--------|
| L1 hit rate ≥ 40% AND L2 ≥ 10% | **SHIP IT** — roll out tiered activation to all new merchants at onboarding |
| L1 30-40% OR L2 5-10% | **ITERATE** — test with WhatsApp-only nudge (no cash incentive) to isolate communication vs money |
| L1 < 30% | **KILL IT** — activation barrier is structural (product/UX), not motivational. Incentives won't fix it. |
| Insufficient data (pool < 30 activations) | **EXTEND** — expand pool to Jan 15+ merchants or wait for more onboards |

**Current trajectory (Feb 23)**: L1=23%, L2=5%. All windows close by Feb 28 — 5 days to final read. The 24 merchants with open windows could push L1 higher. Closed-window cohort (20 merchants) already shows ~35-40% L1, suggesting the incentive is working for merchants who got it early. Final verdict will depend on whether Feb 10-14 cohort (24 merchants, heaviest volume) converts.

**Confirmation metric**: Of merchants who hit Level 1, how many make a sale in the 7 days AFTER the incentive window ends? If <10%, the incentive created artificial behavior that won't persist.

---

## What Prompted This Rewrite

EXP-004 v4 (launched Feb 13) set the bar at $30/3+ customers — a target 10x above organic behavior. After 5 days, zero merchants have hit the target. The data shows the real bottleneck is 0→1 (78% never sell at all), not 1→many. This rewrite shifts focus to the actual leverage point.
