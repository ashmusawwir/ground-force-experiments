# EXP-019: Channel Yield + Flyer Optimization

**STATUS: RUNNING** — Observational measurement of which sourcing channels and flyer variants produce candidates who complete the EOI → Training → Field pipeline, so we can kill underperformers and scale winners.

---

## Scorecard

| Metric | Baseline | Current | Target |
|--------|----------|---------|--------|
| EOI-to-7-day-active conversion by channel | Referral: best signal; Bazaar: 10%; 3PL: 0% | — | ≥1 channel >20% EOI-to-active with sufficient volume |
| EOI volume by channel | No data for WA/FB groups | — | 120+ EOIs across channels |
| Sample | 120+ EOIs from EXP-018 sprint | — | — |

## Hypothesis

Which sourcing channels (WhatsApp groups, Facebook groups, Referral, Direct) produce candidates who complete the full hiring pipeline, and does flyer content affect conversion?

## Success Criteria

- **Scale:** Channel EOI → active > 20% → find more groups like this, post weekly
- **Maintain:** Channel EOI → active 5–20% → keep posting but don't invest more
- **Kill:** Channel EOI → active < 5% → stop posting, reallocate to top channels
- **Build program:** Referral EOI → active > 30% → formalize: each top performer refers 2–3/month
- **Ship flyer variant:** One flyer variant 2× better → all future posts use winning variant
- **Inconclusive if:** All channels roughly equal → channel doesn't matter — maximize volume everywhere

## The Experiment

Historical data shows massive channel variance: Referral (75% show rate) vs 3PL (36% show rate, 0% E2E). The team is now sourcing from new channels (WhatsApp groups, Facebook groups) with no performance data. As EXP-018 runs the hiring sprint, EXP-019 piggybacks to measure which channels actually produce hires. Runs in parallel with the same candidate pool. Analysis only — no channel intervention.

## Minimum Viable Test

- **Intervention:** None — observational. Tag every EOI with source group and channel type in the tracking sheet.
- **Who:** All EOIs from EXP-018 sprint
- **How:** Track full funnel by channel: EOI → training showed → training passed → field → 7-day active. Post flyer to multiple groups across channels in Day 1 blitz. If volume allows, test flyer variants (A: lead with earnings, B: lead with flexibility).
- **Duration:** 1 week (same sprint as EXP-018)
- **Controls:** Cross-channel comparison (same flyer, different groups)

## Results

### What happened

*Sprint in progress.*

### What we learned

*Pending.*

### What we'd do differently

*Pending.*

**Decision:** —
**Decision notes:** —

## What Happens Next

- **Channel kill list:** Day 5 Friday retro — channels below 5% EOI-to-active get cut
- **Scale list:** Channels above 20% get prioritized for all future sprints
- **Assumption update:** Pending sprint completion

## Detail

### Raw Data

Sheet: `1Y3o_BfXk3rdREHEpLc3SBdwWFJd4DfKmuf0hwh-BZYI`

**Historical channel data:**

| Channel | Interview Show Rate | E2E (to live) | Status |
|---------|-------------------|---------------|--------|
| Referral | 75% (3/4) | Best signal (2 PT pending) | Small n but promising |
| Bazaar | 60% (6/10) | 10% (1/10) | Moderate |
| 3PL | 36% (5/14) | 0% (0/14) | Terrible — likely kill |
| Facebook | No data | — | New channel, untested |
| WhatsApp Groups | No data | — | New channel, untested |

### Methodology

**Metrics by channel:**

| Metric | What it tells us |
|--------|-----------------|
| EOI volume | Channel reach — how many people respond? |
| EOIs per 100 group members | Flyer resonance in that audience |
| Training show rate | Channel quality — do these people follow through? |
| Training pass rate | Channel fit — are these the right people for the job? |
| 7-day active rate | Channel durability — do they stick? |
| EOI-to-active conversion | The single number that matters |

**Classification**: ANALYSIS (observation, not intervention). Runs in parallel with EXP-018.

**Tab 1: Candidate Pipeline — "Feb 18 Onwards" (one row per candidate):**

| Column | Type | Who fills | When |
|--------|------|----------|------|
| City | Dropdown | Qasim/Afsar | At EOI |
| Name | Text | Qasim/Afsar | At EOI |
| Phone | Text | Qasim/Afsar | At EOI |
| Source | Text (self-reported: "Where did you hear about us?") | Qasim/Afsar | At EOI |
| Interview Date | Date | Qasim | Interview day |
| Engagement | Dropdown (High / Medium / Low) | Qasim | During interview |
| App Comprehension | Dropdown (Got it / Needed help / Struggled) | Qasim | During interview |
| Comfort w/ Strangers | Dropdown (Natural / Needs coaching / Uncomfortable) | Qasim | During interview |
| Communication | Dropdown (Clear / Adequate / Poor) | Qasim | During interview |
| Qasim Notes | Text | Qasim | End of interview |
| Training Date | Date | Qasim | When scheduled |
| Showed Up | Dropdown (Y / Late / No-show) | Qasim | Training day |
| Pass / Fail | Dropdown (Pass / Fail) | Qasim | End of training |
| Fail Reason | Dropdown (Behavior / Couldn't learn app / Left early / No-show / Other) | Qasim | If Fail |

**Interview note**: Observational only — no one is rejected. Everyone proceeds to training regardless of scores.

**Tab 2: Broadcast Log (one row per flyer post):**

| Column | Type | Example |
|--------|------|---------|
| Date Posted | Date | Feb 18, 2026 |
| Group Name | Text | "Karachi Delivery Jobs" |
| Group Type | Dropdown | WA / FB |
| Est. Members | Number | ~500 |
| Flyer Variant | A / B | A (earnings-led) |
| EOIs Received | Number | 12 |
| Notes | Text | "Very active group" |

### Per-Ambassador Breakdown

N/A — this experiment tracks candidates by channel, not ambassador performance.

### Gate Log

| Date | From | To | Rationale | By |
|------|------|-----|-----------|-----|
| | | | | |

**Kill criteria:**

| Check | Trigger | Authority |
|-------|---------|-----------|
| Day 1 EOI volume | < 50 total EOIs from 20+ groups | Turab — flyer isn't landing, redesign |
| Day 5 channel data | All channels within 5pp of each other | Channel doesn't matter — stop segmenting, maximize volume |
| Day 7 | No channel above 15% EOI-to-active | Problem is pipeline (EXP-018), not channels |

**Absorbs previous experiments:**
- Old EXP-017 (Hiring Tournament): Tournament format was too slow. Channel yield tracked in real-time during sprint.
- Old EXP-019 (Referral Hiring): Referral is one of the channels being measured — no separate experiment needed.
