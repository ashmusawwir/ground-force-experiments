# Experiment Report Standard

The canonical structure for all ground force experiment reports. Reports live on Notion (Experiment Tracker database: `304003b8-300d-8105-b1a5-000bb19137b1`). This document defines the structure and writing rules.

## Scope

- **Home**: Notion Experiment Tracker database. Each experiment = one page.
- **Operating cycle**: IDENTIFY → FOCUS → EXPERIMENT → LEARN → REPEAT (weekly)
- **Team**: Turab (strategy), Qasim (field execution), Asharib (data + systems)
- **Sync cadence**: Wednesday mid-week update, Friday review

---

## 1. Executive Summary Table

Every report opens with this table. No prose before it.

| Element | Detail |
|---------|--------|
| Experiment | EXP-NNN: [Name] |
| Verdict | SHIP IT / ITERATE / KILL IT / NEEDS MORE DATA |
| Primary Metric | [metric]: [baseline] → [result] ([change]) |
| Confidence | [High/Medium/Low] + statistical basis |
| Duration | [start] → [end] ([N] days) |
| Sample Size | [N] treatment, [N] control |
| Next Step | [specific action or next experiment] |

---

## 2. TL;DR

2-3 sentences maximum. What we tested, what happened, what we're doing about it.

---

## 3. Context & Hypothesis

- What data or observation led to this experiment
- Prior experiments that inform this one (reference EXP-NNN)
- **Hypothesis** (experiments): IF [intervention you control] THEN [quantified outcome] BECAUSE [mechanism]
- **Research Question** (analyses): "What [pattern/relationship] exists in [cohort], and what [signals/factors] predict [outcome]?"
- Use hypothesis when you're introducing/changing something. Use research question when you're analyzing what already happened.
- **Falsifiability**: What result would disprove this?
- **Primary metric**: [metric] — observed/reported, source
- **Baseline**: [value] (source, date range)
- **Target**: [value] (rationale for this threshold)

---

## 4. Experiment Design

### 4.1 Setup

- Split type: time-based / person-based / training-based
- Treatment vs control definition
- Duration and sample size rationale
- Data collection method

### 4.2 Assumption Check

Answer inline (not as a gate — weave into the narrative):

1. What has to be true for this to work?
2. What's the riskiest assumption?
3. How can we test it cheaply?
4. Does this create perverse incentives?
5. Does it require ambassador skill/judgment?

### 4.3 Statistical Validity Check

| Check | Answer |
|-------|--------|
| Sample size per variant | [N] — [how determined] |
| MDE | [value] |
| Power / Confidence | [80%/95% or custom] |
| Randomization | [method, contamination risk] |
| Duration covers full cycle? | [yes/no, rationale] |

**Validity verdict**: SUFFICIENT / WEAK / INSUFFICIENT

If WEAK: prefix all claims with "Directional:"
If INSUFFICIENT: flag what's needed before conclusions are valid

---

## 5. Results

### 5.1 Top-Line

| Metric | Control | Treatment | Delta | CI (95%) | Significance |
|--------|---------|-----------|-------|----------|-------------|
| [primary] | [value] | [value] | [+/-X%] | [lower, upper] | [p-value or Bayesian P] |

Mark every metric: (observed) or (reported).

### 5.2 Per-Ambassador Breakdown

| Ambassador | N | Rate | Tier |
|-----------|---|------|------|
| [name] | [visits] | [rate] [CI] | Reliable/Directional/Insufficient |

Tier definitions:
- **Reliable**: n >= 20
- **Directional**: 5 <= n < 20
- **Insufficient**: n < 5

### 5.3 Key Insights

2-4 maximum. Use this format:

> **INSIGHT**: [one-sentence finding]
> **Evidence**: [supporting data]
> **Implication**: [what to do about it]

Tag surprises: **UNEXPECTED**

---

## 6. So What?

- **Goodhart check**: Could gaming explain the improvement?
- **Trend over value**: Is the metric moving in the right direction, even if it hasn't hit target?
- **Ambassador heterogeneity**: Is the effect consistent across ambassadors, or driven by 1-2 individuals?
- **Temporal stability**: Consistent across days, or driven by one anomalous day?

---

## 7. Recommendation

Lead with the verdict (same as executive summary):

| Verdict | Meaning | Action |
|---------|---------|--------|
| SHIP IT | Effect is real and significant | Operationalize — train all ambassadors, update playbook |
| ITERATE | Directional signal, needs refinement | Redesign specific element, run again |
| KILL IT | No effect or negative effect | Stop, document learning, move on |
| NEEDS MORE DATA | Insufficient sample or ambiguous | Extend duration or increase sample |

### Feed-Forward

Every recommendation MUST propose the next hypothesis:
> "This suggests we should test whether [next hypothesis]. Proposed: EXP-NNN."

Experiments don't end — they generate the next question.

---

## 8. Appendix

- Raw data tables (toggle in Notion)
- SQL queries used
- Methodology notes
- Excluded data and rationale

---

## Writing Rules

### No Filler
- Delete every sentence that doesn't add information
- "It's worth noting that" → delete. "Interestingly" → delete. Just state the finding.
- If a section has nothing meaningful, write "No findings" — don't pad it

### Specificity Standard
- Every number needs a source: "(n=42, Feb 10-14 data)"
- Every claim needs evidence: "Demo rate increased" → "Demo rate increased from 7% to 48% (20/42, p<0.01)"
- Reject "improved" without magnitude. Reject "significant" without statistical test.

### Observed Over Reported
- Always flag: (observed) = system/database data, (reported) = ambassador self-report
- When they conflict, observed wins
- Note the discrepancy — the gap between observed and reported is itself a finding

### Storytelling Frame
- Executive summaries for syncs follow: what happened → what needs attention → what we learned
- Every finding should answer "so what?" — if it doesn't change a decision, cut it
- The audience is Turab and Brandon (CEO) — they care about decisions, not methodology

### Narrative Quality
- Write for people who will skim. Bold the verdict, bold the key numbers.
- Use tables for comparison, prose for interpretation
- One insight per paragraph. No compound insights.
