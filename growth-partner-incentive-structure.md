# EXP-004: Merchant Activation Incentive (v5)

> **One-liner**: We're testing whether a tiered cash incentive ($2/$3/$5) can push merchant activation from 22% to 40%+ within 14 days for all merchants onboarded since Feb 1.

---

## The Offer

**Three levels. Each unlocks a cash reward.**

| Level | What You Do | You Earn |
|:-----:|-------------|:--------:|
| 🟢 **First Sale** | Send your first cash note or complete your first order (≥$1) | **$2** |
| 🔵 **Repeat Seller** | Complete 3+ total sales | **$3** |
| 🟡 **Volume Seller** | Reach $10+ in total sales volume | **$5** |

**Maximum you can earn: $10** (by hitting all three levels).

Sales = cash notes you send to customers + orders you fulfill. Amounts under $0.01 don't count.

---

## Who Qualifies

All merchants onboarded to ZAR since **February 1, 2026**.

**Current pool: 49 merchants.**

You have **14 days** from the day you're told about the offer to hit each level.

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
> Level 1 ✅ (first sale) → earns **$2**

**Merchant B** sends 3 cash notes ($2, $3, $1) to 3 different customers:
> Level 1 ✅ + Level 2 ✅ (3 sales, $6 total) → earns **$5**

**Merchant C** fulfills 4 ZCE orders totaling $15:
> Level 1 ✅ + Level 2 ✅ + Level 3 ✅ → earns **$10**

---
---

# Internal: Data-Informed Design Rationale

*Everything above is merchant-facing. Everything below is internal.*

---

## Why These Thresholds (The Data)

**Source**: All 49 merchants onboarded since Feb 1, 2026. Queried Feb 18.

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

## Cost Model

| Scenario | L1 (22→40%) | L2 (0→15%) | L3 (4→10%) | Total Cost |
|----------|:-----------:|:----------:|:----------:|:----------:|
| Conservative | 20 × $2 = $40 | 7 × $3 = $21 | 5 × $5 = $25 | **$86** |
| Optimistic | 22 × $2 = $44 | 10 × $3 = $30 | 8 × $5 = $40 | **$114** |
| Maximum (all 49 hit all 3) | 49 × $10 | — | — | **$490** |

**Cost per activated merchant**: ~$4-6 (vs $10 in v4 for zero activations).

---

## Pre vs Post Incentive (Feb 13 Cutoff)

| Cohort | Size | Organic Sales (pre-13) | Incentive Sales (post-13) |
|--------|:----:|:---------------------:|:------------------------:|
| Onboarded Feb 1-12 | 30 | 8 merchants (27%) | 2 merchants added post-incentive sales |
| Onboarded Feb 13+ | 19 | N/A | 2 merchants (10%) |

The Feb 13+ cohort has lower activation (10% vs 27%) but they've had less time. The incentive period (5 days so far) has not yet measurably moved behavior beyond organic.

**The $105 outlier**: One PE merchant (onboarded Feb 14) sent 2 cash notes totaling $105 during the incentive period. This is either genuine commercial activity or an internal transfer — worth investigating before attributing to the incentive.

---

## Statistical Validity

| Check | Assessment |
|-------|-----------|
| Pool size | 49 — borderline. At 22% organic activation, 95% CI is [12%, 36%]. |
| MDE | Can detect ~15pp lift (22% → 37%) at 80% power. Cannot detect smaller effects. |
| Power verdict | **WEAK** — can detect large effects only. Prefix claims with "Directional." |
| Randomization | None — all qualifying merchants receive the offer. No control group. |
| Temporal confound | Feb 1-12 merchants have more time to activate naturally. Compare within-cohort. |

**What would make it sufficient**: Pool of 80+ merchants (achievable by extending qualifier window to Jan 15+, or waiting for more Feb onboards). Or: withhold the incentive from a random 25 merchants as control.

---

## Fraud Safeguards

| Safeguard | How It Works |
|-----------|-------------|
| **$0.01 filter** | Amounts ≤$0.01 excluded — prevents gaming with test transactions |
| **Distinct customer check** | Each sale must be to a different user — no self-sends or cycling |
| **Independent verification** | ZAR team verifies transactions before payout |
| **$10 cap** | Maximum reward per merchant limits downside |
| **Observed data only** | All metrics from system data (CN + ZCE tables), not self-reported |

---

## Decision Rules

| Result | Action |
|--------|--------|
| L1 hit rate ≥ 40% AND L2 ≥ 10% | **SHIP IT** — roll out tiered activation to all new merchants at onboarding |
| L1 30-40% OR L2 5-10% | **ITERATE** — test with WhatsApp-only nudge (no cash incentive) to isolate communication vs money |
| L1 < 30% | **KILL IT** — activation barrier is structural (product/UX), not motivational. Incentives won't fix it. |
| Insufficient data (pool < 30 activations) | **EXTEND** — expand pool to Jan 15+ merchants or wait for more onboards |

**Confirmation metric**: Of merchants who hit Level 1, how many make a sale in the 7 days AFTER the incentive window ends? If <10%, the incentive created artificial behavior that won't persist.

---

## What Prompted This Rewrite

EXP-004 v4 (launched Feb 13) set the bar at $30/3+ customers — a target 10x above organic behavior. After 5 days, zero merchants have hit the target. The data shows the real bottleneck is 0→1 (78% never sell at all), not 1→many. This rewrite shifts focus to the actual leverage point.
