# EXP-018: Direct-to-Training Pipeline

> **One-liner**: "We're running observational interviews alongside a direct-to-training pipeline to identify which candidate signals predict field success, so we can embed those into the flyer and training at scale."

## Experiment Card

| Element | Detail |
|---------|--------|
| Hypothesis | IF we run observational interviews (no one rejected) alongside a direct-to-training pipeline THEN we'll identify which candidate signals predict field success AND achieve >20% EOI-to-active conversion BECAUSE structured interview data (Engagement, App Comprehension, Comfort w/ Strangers, Communication) correlated with Day 7 retention reveals what to embed in the flyer and training at scale — making the interview removable once we know what it teaches us. |
| Decision This Informs | 1) Which interview signals predict field success? (Embed into flyer/training.) 2) Can this pipeline produce 30 active growth partners in one week? Turab/Qasim decide. |
| Primary Metric | EOI-to-7-day-active conversion rate (observed) |
| Confirmation Metric | 7-day retention rate among training completers |
| Baseline | 3.6% E2E (28 reached → 1 live hire, historical sheet data) |
| Target | >20% EOI-to-active |
| Sample Size | 120+ EOIs (first sprint) |
| Controls | Historical funnel data (call → interview → training → field) as baseline comparison |
| Duration | 1 week sprint (Mon flyer blitz → Sun 7-day count) |

## The Pipeline

```
BROADCAST (Day 1):
  Flyer posted to 20+ WA/FB groups
  Reach: 5,000+ combined members

TRACKABLE FUNNEL:
  ① EOI received (WhatsApp message)        ← funnel starts here
  ② Interview (Qasim, in-person, OBSERVATIONAL)
     No one rejected — everyone proceeds to training
     Structured eval: Engagement, App Comprehension,
     Comfort w/ Strangers, Communication
  ③ Training & Field
     Qasim evaluates pass/fail DURING training
  ④ 7-day active check (from visits sheet)
```

### The Interview as a Research Instrument

The interview is **observational** — no candidate is rejected. Everyone proceeds to training regardless of interview scores. The purpose is to collect structured data on 4 dimensions so we can later correlate interview signals with field success (Day 7 retention).

**Learning question**: "What can we learn from the interviews that can apply to what we do at scale?"

| Interview Signal | What it measures | At scale, this becomes... |
|-----------------|-----------------|--------------------------|
| Engagement | Did they pay attention, ask questions? | Training eval criterion |
| App Comprehension | Could they follow the demo? | Training eval criterion |
| Comfort w/ Strangers | Would they approach a shopkeeper? | Flyer filter ("comfortable talking to shopkeepers") |
| Communication | Can they explain the app? | Training eval criterion |

**Learning output**: After the sprint, build a **Signal → Retention Correlation Matrix**: for each of the 4 criteria, what % of candidates who scored High/Got it/Natural/Clear are still active at Day 7 vs those who scored Low/Struggled/Uncomfortable/Poor? Signals with strong correlation get embedded into the flyer (self-selection) and training rubric (evaluation). Once embedded, the interview can be removed.

## Sprint Schedule

| Day | Action | Output |
|-----|--------|--------|
| Mon | Flyer blitz to 20+ WA/FB groups | 120+ EOIs |
| Tue | Interviews (Qasim, in-person, observational) + Training (AM/PM) | 16-20 interviewed + trained |
| Wed | Batch 1+2 → field. More interviews + training | 16-20 more |
| Thu | Remaining → field. Mop-up interviews + training | All in field |
| Fri | Retro: what worked? | Channel decisions |
| Sun | 7-day count | 30 active? |

### Sprint Math (backwards from 30)

```
Need: 30 active on Day 7
  ← 40 field starters (75% survive first week)
    ← 48 training passers (85% pass rate)
      ← 65 show for training (75% show rate of scheduled)
        ← 100 scheduled for training (65% of EOIs respond to scheduling)
          ← 120-150 EOIs received
```

**Training capacity**: Qasim runs batches of 8-10, twice daily = 16-20 trained/day. Over 2-3 training days = 40-60 trained. Enough for 30 active.

## Decision Rules

| Result | Action |
|--------|--------|
| EOI → active > 20% AND no field incidents | **SHIP IT** — pipeline works. Build Signal → Retention matrix, embed learnings into flyer/training, remove interview in next sprint. |
| EOI → active 10-20% | **ITERATE** — which step is leaking? Use interview data to identify what predicts dropout. Tighten flyer or training based on signal correlations. |
| EOI → active < 10% | **KILL IT** — pipeline doesn't produce hires. Check if interview signals predicted the failures — if yes, the interview may need to become a gate (not just observational). |
| Training show < 50% | Flyer isn't filtering enough — revise content, add same-day confirmation call |
| Training rejection > 30% | Too many bad fits — flyer needs harder filters (more explicit about walking, talking to strangers) |
| Any field incident (brand damage) | **PAUSE** — add Afsar phone screen for remaining batches |

**Confirmation metric rule**: if EOI-to-active looks good but 7-day retention is <50%, the pipeline is producing tourists not workers — classify as ITERATE at best.

## Kill Criteria

| Check | Trigger | Authority |
|-------|---------|-----------|
| Day 1 EOI volume | < 50 EOIs from 20+ groups | Turab — redesign flyer, repost Day 2 |
| Day 2 training show | < 50% of scheduled showed | Qasim — add same-day confirmation call |
| Day 3 field behavior | Any brand damage incident | Qasim — pause, add phone screen gate |
| Day 7 retention | < 50% of field starters active | Turab — pipeline produces low-commitment hires |

## Context

### Prior experiments

| EXP | What we learned | How it informs this experiment |
|-----|----------------|-------------------------------|
| Historical hiring sheet (28 candidates) | 52% interview no-show, 71% training no-show, 3.6% E2E. 3PL channel = 0% conversion. | Overnight gaps between stages cause massive attrition. Removing the interview eliminates the biggest no-show cliff. |
| EXP-017 (deleted, was Hiring Tournament) | Never ran — tournament format too slow for 30-hire target | Replaced by real-time channel tracking in EXP-019 |
| EXP-019 (deleted, was Referral Hiring) | Referral channel showed 75% interview show rate (best of all channels) | Referral folded into EXP-019 as one of the tracked channels |

### What prompted this

The team needs ~30 growth partners but the current funnel converts at 3.6% (28 → 1). Two overnight gaps (call→interview, interview→training) cause 52% and 71% no-show rates respectively. The insight: the interview is redundant — the flyer can handle fit-screening and training can handle behavior-screening. Removing the interview and compressing to a 1-week sprint eliminates both no-show cliffs.

## Assumption Check

1. **What has to be true?** The flyer must be specific enough to filter bad fits. The observational interview must produce enough structured data to correlate signals with outcomes. Qasim can handle interviews + batch training.
2. **Riskiest assumption?** That the 4 interview signals (Engagement, App Comprehension, Comfort w/ Strangers, Communication) actually predict field success. If they don't correlate, we've collected data that doesn't inform scale decisions.
3. **Cheap test?** First batch through the full pipeline (interview → training → field). Check if Qasim's interview scores for Batch 1 align with their Day 3 field performance.
4. **Perverse incentives?** No — interview is observational (no rejection), so candidates can't game it. Qasim evaluates honestly because the scores don't affect the candidate's progression.
5. **Ambassador skill/judgment?** Yes — Qasim must evaluate during both interview and training. Structured dropdowns reduce subjectivity but judgment is still required.

## Statistical Validity

| Check | Answer |
|-------|--------|
| Sample size | 120+ EOIs, 40+ trained — sufficient for directional read |
| MDE | Comparing to 3.6% baseline, any result >10% is a meaningful improvement |
| Power/Confidence | Not a controlled experiment — before/after comparison. Treat all results as directional. |
| Randomization | None — all EOIs go through the same pipeline. Channel comparison (EXP-019) provides some segmentation. |
| Duration | 1 week covers the full hiring cycle (EOI → field → 7-day check) |

**Validity verdict**: WEAK (no control group, before/after comparison only). Prefix claims with "Directional:". But the historical baseline is so bad (3.6%) that even a directional improvement is actionable.
