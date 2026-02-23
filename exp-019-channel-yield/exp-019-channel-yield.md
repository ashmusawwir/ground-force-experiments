# EXP-019: Channel Yield + Flyer Optimization

> **One-liner**: "We're measuring which sourcing channels and flyer variants produce candidates who complete the EOI → Training → Field pipeline, so we can kill underperformers and scale winners."

## Experiment Card

| Element | Detail |
|---------|--------|
| Research Question | Which sourcing channels (WhatsApp groups, Facebook groups, Referral, Direct) produce candidates who complete the full hiring pipeline, and does flyer content affect conversion? |
| Decision This Informs | Where to allocate sourcing effort for future hiring sprints. Turab/Qasim decide. Kill channels <5% EOI-to-active, scale channels >20%. |
| Primary Metric | EOI-to-7-day-active conversion rate by channel (observed) |
| Confirmation Metric | EOI volume by channel (a great channel with no volume is useless) |
| Baseline | Historical: Referral 75% interview show, Bazaar 60%, 3PL 36% (0% E2E) |
| Target | At least 1 channel with >20% EOI-to-active AND sufficient volume |
| Sample Size | 120+ EOIs across channels (from EXP-018 sprint) |
| Controls | Cross-channel comparison (same flyer, different groups) |
| Duration | 1 week (same sprint as EXP-018) |

## Classification

ANALYSIS (observation, not intervention). We're not changing channels — we're measuring which ones work. Runs in parallel with EXP-018 using the same candidate pool.

## Historical Channel Data

| Channel | Interview Show Rate | E2E (to live) | Status |
|---------|-------------------|---------------|--------|
| Referral | 75% (3/4) | Best signal (2 PT pending) | Small n but promising |
| Bazaar | 60% (6/10) | 10% (1/10) | Moderate |
| 3PL | 36% (5/14) | 0% (0/14) | Terrible — likely kill |
| Facebook | No data | — | New channel, untested |
| WhatsApp Groups | No data | — | New channel, untested |

## Design

- Tag every EOI with source group and channel type in the tracking sheet
- Track full funnel by channel: EOI → training showed → training passed → field → 7-day active
- Post flyer to multiple groups across channels in Day 1 blitz
- If volume allows, test flyer variants (A: lead with earnings, B: lead with flexibility)
- Review channel data on Day 5 (Friday retro) and Day 7

### Metrics by Channel

| Metric | What it tells us |
|--------|-----------------|
| EOI volume | Channel reach — how many people respond? |
| EOIs per 100 group members | Flyer resonance in that audience |
| Training show rate | Channel quality — do these people follow through? |
| Training pass rate | Channel fit — are these the right people for the job? |
| 7-day active rate | Channel durability — do they stick? |
| EOI-to-active conversion | The single number that matters |

## Decision Rules

| Result | Action |
|--------|--------|
| Channel EOI → active > 20% | **SCALE** — find more groups like this, post weekly |
| Channel EOI → active 5-20% | **MAINTAIN** — keep posting but don't invest more |
| Channel EOI → active < 5% | **KILL** — stop posting, reallocate to top channels |
| Referral EOI → active > 30% | **BUILD PROGRAM** — formalize: each top performer refers 2-3/month |
| One flyer variant 2x better | **SHIP** — all future posts use winning variant |
| All channels roughly equal | Channel doesn't matter — maximize volume everywhere |

## Tracking

Sheet: `1Y3o_BfXk3rdREHEpLc3SBdwWFJd4DfKmuf0hwh-BZYI`

### Tab 1: Candidate Pipeline — "Feb 18 Onwards" (one row per candidate)

Single tab covering the full pipeline: EOI → Interview → Training → Field. Day 3/Day 7 retention tracked from the visits sheet.

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

**Conditional formatting**: Green = Pass. Red = No-show or Fail. Yellow = Has interview date but no Pass/Fail yet (in progress).

**Learning output**: After the sprint, correlate interview scores with field retention (from visits sheet) to identify which of the 4 interview signals predict Day 7 success → embed predictive signals into flyer and training at scale.

### Tab 2: Broadcast Log (one row per flyer post)

| Column | Type | Example |
|--------|------|---------|
| Date Posted | Date | Feb 18, 2026 |
| Group Name | Text | "Karachi Delivery Jobs" |
| Group Type | Dropdown | WA / FB |
| Est. Members | Number | ~500 |
| Flyer Variant | A / B | A (earnings-led) |
| EOIs Received | Number | 12 |
| Notes | Text | "Very active group" |

## Context

### What prompted this

Historical data shows massive channel variance: Referral (75% show rate) vs 3PL (36% show rate, 0% E2E). The team is now sourcing from new channels (WhatsApp groups, Facebook groups) with no performance data. As EXP-018 runs the hiring sprint, EXP-019 piggybacks to measure which channels actually produce hires.

### Absorbs previous experiments

- **Old EXP-017 (Hiring Tournament)**: The tournament format (3 pools × 3 candidates, 5-day trial) was too slow. Channel yield is now tracked in real-time during the sprint.
- **Old EXP-019 (Referral Hiring)**: Referral is one of the channels being measured. Top performers should refer candidates into the same pipeline — no separate experiment needed.

## Kill Criteria

| Check | Trigger | Authority |
|-------|---------|-----------|
| Day 1 EOI volume | < 50 total EOIs from 20+ groups | Turab — flyer isn't landing, redesign |
| Day 5 channel data | All channels within 5pp of each other | Channel doesn't matter — stop segmenting, maximize volume |
| Day 7 | No channel above 15% EOI-to-active | Problem is pipeline (EXP-018), not channels |
