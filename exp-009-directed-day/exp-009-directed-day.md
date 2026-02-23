# EXP-009: Directed Day — Structured Ambassador Task Lists

## Experiment Card

| Element | Detail |
|---------|--------|
| Hypothesis | IF ambassadors receive a daily directed task list of 8 geo-clustered visits (mix of onboarding revisits + reactivation visits) with clear per-visit objectives and geofenced verification, THEN onboarding conversion on directed revisits will exceed 30% and merchant reactivation rate within 7 days will exceed 40%, BECAUSE structure eliminates route inefficiency, warm-lead neglect, and unclear visit objectives. |
| Primary Metric 1 | Onboarding conversion rate on directed revisits (observed: merchant appears in `merchant_onboarding_submissions` within 48h of visit) |
| Primary Metric 2 | Reactivation rate on directed visits (observed: merchant has ZCE or cash note transaction within 7 days of visit) |
| Baseline | Onboarding: ~0% revisit-to-onboard rate (only 38/832 visits are revisits, none systematically targeted). Reactivation: 88% of onboarded merchants are 14-day inactive with no follow-up system. |
| Target | Onboarding ≥30%, Reactivation ≥40% |
| Sample Size | 130 Karachi merchants (76 onboarding targets + 54 reactivation targets) |
| Controls | Autonomous free-roam visits on the same days (remaining ~7 visits/day after 8 directed) serve as within-day control |
| Duration | Baseline = historical visit sheet data → Directed period starts when companion app is ready |

## Decision Rules

| Result | Action |
|--------|--------|
| Onboarding >30% AND reactivation >40% | **SHIP IT** — directed day becomes default operating model |
| One metric hits target, other directional | **ITERATE** — adjust task mix, keep the working lever |
| Neither metric improves over baseline | **KILL IT** — structure doesn't help, invest in ambassador selection instead |
| <30 directed visits per pool after 2 weeks | **EXTEND** — need more data, continue experiment |

## Context

### The Problem

Ambassadors currently have full autonomy — no area restriction, no designated shops, shops scattered across the city. The current focus is onboarding (not revisits). Two untapped pools exist:

1. **Warm leads decaying**: 140 merchants got demos but never onboarded (101 with GPS). No one follows up.
2. **Dormant merchants**: Only 12% (20/161) of all onboarded merchants are active in the last 14 days. 88% are dormant with zero follow-up system.

### Merchant Pool (Feb 13, 2026 — DB verified)

| City | Total Merchants | Active (14d) | Inactive (14d) | Inactive with GPS |
|------|----------------|-------------|----------------|-------------------|
| Lahore | 99 | 8 | 91 | 91 |
| **Karachi** | **60** | **12** | **48** | **48** |
| Punjab | 2 | 0 | 2 | 2 |
| **Total** | **161** | **20** | **141** | **141** |

### Visit Sheet Pool (demoed but not onboarded)

| Metric | Count |
|--------|-------|
| Total demo-no-onboard visits | 140 |
| With GPS coordinates | 101 |
| With merchant phone | 78 |
| With shop name | 140 |
| Karachi only (filtered by lat/lng) | 76 |

### Combined Karachi Pool: 130 merchants

- 76 onboarding targets (demoed, not onboarded, with GPS)
- 54 reactivation targets (onboarded merchants, all with GPS)
- At 24 directed visits/day (3 ambassadors × 8): ~5.4 days to cover full pool
- Both pools replenish naturally (rolling 14-day inactivity + new demos daily)

## Design

### Daily Structure

- **8 guided visits per ambassador per day** from combined pool, geo-clustered
- Mix of onboarding revisits + reactivation visits (natural mix based on zone composition)
- **Remaining ~7 visits**: autonomous free-roam (within-day comparison)

### Geo-Clustering: Zones → Daily Routes

Karachi merchants span 20km × 19km. Forcing exactly 8 per k-means cluster degrades walkability (50% of clusters span 5-11km). Solution:

1. **Geographic zones** (Layer 1, weekly): K-means with K≈25-30, variable size 3-12 merchants, all ≤2km radius
2. **Daily routes** (Layer 2, daily): Compose exactly 8 visits per ambassador from 1-2 adjacent zones, prioritizing longest-unvisited merchants

### Activation Visit Objective

Ambassador walks into a 14-day-inactive merchant with:
1. Tell them about the current incentive
2. Do a dummy transaction together (self-purchase + trader purchase)
3. Goal: merchant transacts independently within 7 days

### Onboarding Visit Objective

Ambassador revisits a merchant who got a demo but didn't onboard:
1. Reference the previous demo ("Last time you saw how ZAR works...")
2. Address the reason they didn't onboard (if known from visit form: "Wants to think about it", "Needs owner approval", etc.)
3. Complete onboarding on the spot

### Geofenced Verification

- Ambassador must be within 200m of target merchant GPS to submit the visit form
- Companion app (PWA, similar to agent-app) shows task list with map, requires geofenced check-in
- Geofence radius: start at 200m, tune to 150m if compliance is high, 300m if false rejects are frequent

### Split

**Time-based**: Historical visit sheet data = autonomous baseline → Directed day period begins when companion app is ready.

### Secondary Metrics

- Task completion rate (compliance: did ambassador complete all 8 directed visits?)
- Geofence verification rate (was ambassador actually at the GPS location?)
- Time per directed visit vs autonomous visit
- Total daily onboardings per ambassador (directed vs autonomous period)

## Statistical Validity

| Check | Assessment |
|-------|-----------|
| Sample size | 130 merchants total, ~24 directed visits/day. At 30% target conversion, need ~50 visits for 80% power → achievable in ~2 days |
| MDE | With n=60 per pool, MDE ≈ 15-20pp at 80% power, 95% confidence. Target effects (30%, 40%) are well above MDE |
| Randomization | N/A — time-based split, all ambassadors participate. Contamination risk: ambassadors may improve overall skill from directed training (positive spillover) |
| Duration | 2 weeks minimum to cover full pool + observe 7-day reactivation outcomes |
| **Verdict** | **SUFFICIENT** — proceed with confidence |

## Prior Experiments That Inform This

| Experiment | Key Finding | Relevance |
|-----------|-------------|-----------|
| EXP-001 (Show Don't Tell) | Demo-first opener increased demo rate from 7% to 48% | Directed visits should use demo-first opener |
| EXP-006 (Question Redirect) | "Let me show you" redirect improved Q→Demo conversion | Onboarding revisit talking points should include redirect |
| EXP-007 (Post-Demo Transactions) | Median time to first activity: ~43 minutes, 100% act within 24h | Reactivation visits may see quick results; check within 24-48h |
| Demo Dollars Usage | 12/32 recipients "understood the product" | Revisit targeting should prioritize merchants who showed product understanding |
