# Ground Force Experimentation OS

> **Last updated:** 2026-02-25
> **Aligned with:** Empirium experiment data model, Canon/Praxis agent framework
> **Experiment format:** [v2 Template](https://www.notion.so/zardotapp/TEMPLATE-Experiment-Format-v2-312003b8300d81aea036ff0937dd2518) — Empirium `description` field follows this structure

---

## 1. Operating Structure

### Weekly Cycle
```
IDENTIFY --> FOCUS --> EXPERIMENT --> LEARN --> REPEAT
```

| Step | What happens | Who |
|------|-------------|-----|
| **IDENTIFY** | Spot anomalies in funnel data, surface strategic questions from Delta teams, review Brandon's research priorities | Turab + Asharib |
| **FOCUS** | Rank by urgency x leverage x speed-to-insight. Pick highest-impact experiment. | Turab |
| **EXPERIMENT** | Design experiment (hypothesis, success criteria, MVT). Execute in field. | Turab designs, Qasim executes, Asharib builds data visibility |
| **LEARN** | Document outcome, update assumptions, feed into playbook | All |

### Experiment Sources
| Source | Description | Example |
|--------|-------------|---------|
| Data-driven | Asharib/Turab spot anomalies in funnel data | "90% drop-off between opener and demo -- why?" |
| Team-directed | Turab/Qasim define experiments based on what we need to learn | "Can we activate merchants in 1 day?" |
| Strategic | Aligned with Delta teams or Brandon's research priorities | "Would merchants respond to gold as an offering?" |

### Team Roles
| Step | Turab | Qasim | Asharib |
|------|-------|-------|---------|
| IDENTIFY | Reviews data, defines experiments, maintains backlog | Reports field observations | Pulls data, builds dashboard views |
| FOCUS | Picks top experiment, writes rationale | Input on field feasibility | Provides data cuts |
| EXPERIMENT | Designs experiment, sets metrics | Executes in field, ensures compliance | Creates experiment-specific data visibility |
| LEARN | Documents learnings, presents to leadership | Shares ambassador feedback | Final data pull, analysis |

---

## 2. Experiment Lifecycle (Empirium State Machine)

Every experiment follows a strict state machine. Status and Decision are **separate concepts**.

### Status States
```
Design --> Running --> Analyzing --> Complete
                                 \-> Abandoned (from any state)
```

| Status | What it means | Who sees it |
|--------|--------------|-------------|
| **Design** | Experiment designed, not yet running. Hypothesis and success criteria being defined. | Internal only |
| **Running** | Active data collection in the field. | Internal only |
| **Analyzing** | Data collection complete. Processing results and forming decision. | Internal only |
| **Complete** | Decision made. Results documented. | Everyone (syncs, showcases) |
| **Abandoned** | Stopped early. Reason and learnings documented. | Internal only |

### Decision (only set when Complete)
| Decision | Meaning |
|----------|---------|
| **Validated** | Hypothesis confirmed. Findings are strong enough to act on. |
| **Invalidated** | Hypothesis disproved. Evidence shows the intervention doesn't work. |
| **Inconclusive** | Not enough evidence either way. Need more data or a redesigned experiment. |

### Gate Requirements (status transitions)

Every status transition requires documented rationale. These are the required fields at each gate:

| Transition | Required before moving |
|------------|----------------------|
| **Design --> Running** | hypothesis, success_criteria, minimum_viable_test, target_date |
| **Running --> Analyzing** | preliminary observations, data collection status |
| **Analyzing --> Complete** | results, decision (validated/invalidated/inconclusive), decision_notes |
| **Any --> Abandoned** | reason + what_we_learned |

---

## 3. Experiment Data Model (Empirium)

These properties are Empirium's live data model. Each maps to an Empirium field.

| Property | Type | Options / Format |
|----------|------|-----------------|
| **Experiment** | title | `EXP-0XX: Name` |
| **Status** | select | `Design`, `Running`, `Analyzing`, `Complete`, `Abandoned` |
| **Decision** | select | `Validated`, `Invalidated`, `Inconclusive`, `--` |
| **Health** | select | `On Track`, `At Risk`, `Off Track` |
| **Priority** | select | `Urgent`, `High`, `Medium`, `Low` |
| **Focus** | select | `Merchant Acquisition`, `Merchant Activation`, `Ambassador Recruitment`, `Ambassador Training`, `Expansion`, `Growth` |
| **Timeframe** | select | `1 Week`, `2 Weeks`, `1 Month`, `1 Quarter` |
| **Lead** | person | Experiment owner |
| **Metric** | relation | Linked metric being moved |
| **Initiative** | relation | Parent strategic initiative |
| **Start Date** | date | When data collection begins |
| **Target Date** | date | When decision is expected |
| **Assumptions** | rich_text | Which assumptions this experiment tests |

---

## 4. Experiment Page Template

Every experiment's Empirium `description` field follows this structure. Use the [v2 template](https://www.notion.so/zardotapp/TEMPLATE-Experiment-Format-v2-312003b8300d81aea036ff0937dd2518) as reference. Local `.md` experiment cards use the same section headings (standard Markdown, no toggles).

### State Banner (callout, top of page)

Full-width colored callout. Nothing before it.

| Color | Status |
|-------|--------|
| Blue | Design / Running |
| Yellow | Analyzing |
| Green | Complete: Validated |
| Gray | Complete: Invalidated / Inconclusive |
| Red | Abandoned |

**Formats:**
- Design: `DESIGN -- [One-line: what we're testing and what question it answers.]`
- Running: `RUNNING (Day X/Y) -- [Metric so far]. [Trajectory.]`
- Analyzing: `ANALYZING -- Data collected. [Key preliminary observation.]`
- Complete: `VALIDATED / INVALIDATED / INCONCLUSIVE -- [Primary metric with delta]. [One-line so-what.]`
- Abandoned: `ABANDONED -- [Reason]. [What we learned.]`

### Scorecard (visible, not collapsed)

| Row | Content |
|-----|---------|
| **Primary Metric** | `[metric]: Baseline [X] | Current [Y] | Target [Z]` |
| **Confirmation Metric** | Same outcome measured by a different method, or a post-hoc validity check |
| **Sample** | Design: `[N target] over [duration]` / Running: `[N collected] of [N target]` / Complete: `[N total] over [actual duration]` |

---

### Toggle Heading: Hypothesis

> IF [intervention], THEN [outcome], BECAUSE [mechanism].

Write a falsifiable, specific hypothesis. This is the experiment's identity. It cannot change after the experiment moves to Running.

---

### Toggle Heading: Success Criteria

Pre-committed before Running. These **cannot change** after data collection begins.

- **Validated if:** [specific measurable condition]
- **Invalidated if:** [specific measurable condition]
- **Inconclusive if:** [e.g., insufficient sample, confounding variable]

---

### Toggle Heading: The Experiment

**50 words max.** Answers: what prompted this --> what we're testing --> what decision it informs.

- One number max (the baseline or bottleneck metric)
- No methodology, no caveats
- Written for someone who has never seen this experiment
- Context = 1 number + 1 sentence: the bottleneck that made this necessary

---

### Toggle Heading: Minimum Viable Test

Required before status can move to Analyzing.

- **Intervention:** what's different from the control
- **Who:** target population and selection criteria
- **How:** method (A/B, interview, observation, survey)
- **Duration:** planned timeline
- **Controls:** what's held constant

---

### Toggle Heading: Results

Required before status can move to Complete.

**What happened**
Data, numbers, observations. Use standardized funnel terminology -- always prefix conversion rates (e.g., "demo-to-onboarding conversion: 42%", never just "conversion rate: 42%").

**What we learned**
3 insights max. Each with a "so what?" implication. If you have 4+, pick the 3 that change decisions.

**What we'd do differently**
Hindsight improvements for future experiments.

**Decision:** Validated / Invalidated / Inconclusive
**Decision notes:** Rationale for the decision.

---

### Toggle Heading: What Happens Next

- **Next experiment:** [link to follow-up experiment if applicable]
- **Assumption update:** [which assumption, old confidence --> new confidence]
- **Implementation:** [what action, who owns it]

---

### Toggle Heading: Detail (collapsed, for audit)

Contains nested toggles:

**Raw Data** -- Full data tables, Google Sheets links, SQL queries, Amplitude dashboards.

**Methodology** -- How we collected data, controlled variables, measured outcomes. Statistical validity assessment. Jargon acceptable here but must include plain-English parenthetical on first use.

**Per-Ambassador Breakdown** -- Individual performance splits. Tier definitions:
- **Reliable:** n >= 20
- **Directional:** 5 <= n < 20
- **Insufficient:** n < 5

**Gate Log** -- All status transitions with rationale and dates.

| Date | From | To | Rationale | By |
|------|------|-----|-----------|-----|
| | | | | |

---

## 5. Writing Rules

### Funnel Terminology Standard
**Always prefix conversion rates.** "Conversion rate: 42%" is banned. Use:
- "demo-to-onboarding conversion: 42%"
- "opener-to-demo conversion: 7%"
- "visit-to-onboarding conversion: 5%"
- "interested-to-onboarded GP conversion: 12%"

This prevents context poisoning when LLMs process the corpus and when humans read across experiments.

### No Filler
Delete every sentence that doesn't add information. "It's worth noting that" --> delete. "Interestingly" --> delete. Just state the finding.

### Specificity Standard
Every number needs a source: "(n=42, Feb 10-14 data)". Every claim needs evidence: "Demo rate increased" --> "Demo rate increased from 7% to 48% (20/42)". Reject "improved" without magnitude.

### Observed Over Reported
Always flag: (observed) = system/database data, (reported) = ambassador self-report. When they conflict, observed wins. The gap between observed and reported is itself a finding.

### Denominator Rule
When citing a fraction, always use the full population denominator. If data coverage is partial, state coverage separately.

### Selection Bias Rule
If any data source has known selection bias, report TWO rates:
- Comparable rate (excl. biased data) as the headline
- Pooled rate (incl. biased data) as a parenthetical

### Plain Language
- **Sections visible to all:** No statistical jargon. No P-values, Beta distributions, CI, MDE. Replace with plain English.
- **Detail toggles:** Jargon acceptable but must include a plain-English parenthetical on first use.
- **Test:** Read each sentence aloud. If someone who took one stats course 5 years ago would need to Google a term, add a parenthetical.

### Storytelling Frame
Every finding must answer "so what?" -- if it doesn't change a decision, cut it. The audience is Turab and Brandon -- they care about decisions, not methodology.

---

## 6. Learnings Structure (Empirium-aligned)

Every completed experiment produces structured learnings:

| Field | Content |
|-------|---------|
| **What happened** | Factual summary of the experiment outcome |
| **What we learned** | Insights and implications for the business |
| **What we'd do differently** | Hindsight improvements for future experiments |

Learnings should flag cross-team relevance when applicable (e.g., findings that inform Delta teams).

---

## 7. Assumptions Tracking

Experiments test assumptions. Each assumption has a confidence level that updates as evidence accumulates:

| Confidence | Meaning |
|------------|---------|
| **Zero** | No evidence at all |
| **Unknown** | Haven't tested this |
| **Low** | Some evidence, not enough to act |
| **Medium** | Enough evidence for directional decisions |
| **High** | Strong evidence, safe to build on |

Categories: `business_model`, `customer`, `market`, `technical`, `operational`, `financial`

When an experiment completes, update the linked assumption's confidence level and note the evidence.

---

## 8. Brandon's Three Priority Metrics

These are the three metrics with the most room for improvement (identified Feb 20, 2026 Friday sync). All experiments should ladder up to at least one:

1. **Interested GP --> Onboarded GP** (hiring funnel conversion)
2. **Opener --> Demo** (merchant acquisition first contact)
3. **Demo --> Onboarded Merchant** (merchant conversion)

---

## 9. Data Sources

- **Visit form:** Google Sheet `1bFf0NAQFFXIYYxMC1yJeqowRz6MwT_-xawZeg5H9wUQ` / "Visits" tab
- **CRITICAL:** Filter by Visit Type = "New Onboarding" (column G) -- excludes Revisit type visits
- **Onboarded** = Column AD "Merchant Wants To Onboard" (TRUE/Yes)
- **Demo** = Golden Flow Amount column (any non-null value)
- **PostgreSQL** via Metabase -- backend transaction and user data
- **Amplitude** -- app analytics (app opens, sessions)

---

## 10. Where This Lives

- **Empirium** — System of record. All live experiment status, findings, learnings. Team: sigma.
- **GitHub** — `ground-force-experiments` repo. Code, analysis scripts, experiment cards (.md).
- **Notion (Archive)** — Historical experiment pages. Read-only reference. Not updated going forward.
- **Wednesday Sync** — Mid-week update for Brandon/Daniel
- **Friday Showcase** — Weekly presentation of experiment journey and findings
