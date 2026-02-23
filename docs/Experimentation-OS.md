# Experiment Report Standard

The canonical structure for all ground force experiment reports. Reports live on Notion (Experiment Tracker database: `304003b8-300d-8105-b1a5-000bb19137b1`). This document defines the report structure and writing rules. Helix reads this as its authoritative source.

---

## Experiment States

Every page is in one of three states. The state determines which sections are visible and what the banner says.

| State | Banner Color | Audience | Trigger |
|-------|-------------|----------|---------|
| **Planned** | Blue | Merchant sync + internal | Before data collection starts |
| **In Progress** | Blue | Internal only | Active data collection |
| **Completed** | Green / Yellow / Red | Merchant sync + internal | Post-verdict |

**Merchant sync rule:** Only **Planned** and **Completed** experiments are shown in the merchant sync. In-Progress pages are for internal alignment only.

### State Banner Formats

- **Planned**: `PLANNED — Starting [date]. [One-line: what we're testing and the question it answers.]`
- **In Progress**: `IN PROGRESS (Day X/Y) — [Metric so far]. [Trajectory.] ⚠️ [Any blockers]`
- **Completed**: `SHIP IT / ITERATE / KILL IT — [Primary metric with delta]. [One-line so-what.]`

---

## Page Structure: 3 Layers, 10 Sections

Every report follows a funnel — not a catalog. Each section serves one reader at one depth.

### Layer 1 — The Scan (30 seconds, all states)

| # | Section | Format | Max Length |
|---|---------|--------|------------|
| 0 | **State Banner** | Colored callout (green/yellow/red/blue) | 1-3 sentences |
| 1 | **Scorecard** | 5-row table | 5 rows, never more |

### Layer 2 — The Read (2 minutes, state-aware)

| # | Section | States | Format | Max Length |
|---|---------|--------|--------|------------|
| 2 | **The Experiment** | All | Prose paragraph | ~50 words |
| 2.5 | **Design Brief** | Intervention experiments only | 1 compact table | 1 table, 3–5 rows |
| 3 | **Decision Criteria** | All | Simplified decision rules table + 1 plain-English criterion | ~100 words |
| 4 | **Scale & Confidence** | All | Prose | ~80 words |
| 5 | **Early Signals** | In-Progress only | Headline callout + comparison table + 1 implication line | ~300 words |
| 6a | **What Happens Next** | In-Progress only | Single bullet | 1 sentence |
| 5 | **What We Found** | Completed only | Final comparison table + 2-3 insight callouts | ~400 words |
| 6 | **What To Do Next** | Completed only | Numbered list with owners | 3-5 bullets |

*Sections 5 and 6 are state-conditional: Early Signals appears only In-Progress; What We Found and What To Do Next appear only Completed.*

### Layer 3 — The Audit (full read, all states, all collapsed)

| # | Section | Format | Always Collapsed |
|---|---------|--------|-----------------|
| 7 | **Breakdown Detail** | Toggle with table | Yes |
| 8 | **How We Tested This** | Toggle: context, hypothesis, design, validity | Yes |
| 9 | **Decision Contract** | Toggle: decision rules + kill criteria + Planned Actions (In-Progress) | Yes |
| 10 | **Appendix** | Toggle: raw data, SQL, methodology | Yes |

---

## Section-by-Section Spec

### 0. State Banner

Full-width colored callout, first thing on the page. Nothing before it.

- **Blue = PLANNED** — experiment designed, not yet running
- **Blue = IN PROGRESS** — live experiment, internal only
- Green = SHIP IT, Yellow = ITERATE / NEEDS MORE DATA, Red = KILL IT
- **Gating blockers** get a warning flag inline: if something must be resolved before the experiment can conclude, it goes in the banner, not buried in a toggle
- **Length**: 1 sentence for Planned. 1-2 sentences for Completed. Up to 3 for IN PROGRESS (status + trajectory + blocker are three distinct elements).

Examples:
- Planned: `PLANNED — Starting Mar 1. Testing whether structured nighttime routes improve onboardings/hour post-Taraweeh.`
- In-progress: `IN PROGRESS (Day 5/14) — L1 activation 18% (9/49). Trending toward SUFFICIENT. ⚠️ L2 fraud vulnerability must be mitigated before payout.`
- Completed: `ITERATE — Q→Demo: 18% → 21% (+3pp), target 45%. Complete 7-day observation by Feb 22.`
- Multi-part: `MIXED — Pipeline SHIP (22% EOI-to-active vs 20% target). Signals ITERATE (Engagement strong, Communication inconclusive).`

---

### 1. Scorecard

Exactly 5 rows:

| Field | Content |
|-------|---------|
| Primary Metric | `[metric]: [baseline] → [result] ([delta])` |
| Confirmation | `[metric]: [value]` — only if it contradicts/qualifies primary |

Confirmation is for one of two uses only:
- (A) Same outcome measured by a different method (observed vs. reported)
- (B) A post-hoc validity check that tests if behavior will persist (e.g., "Do merchants sell again 7 days after the incentive ends?")

Do NOT use Confirmation for a secondary metric that measures a different outcome (e.g., L2 rate is not a confirmation of L1 — it's a separate tier).

| Confidence | `High/Medium/Low — [one-phrase basis]` (not Beta distributions) |
| Sample | Planned: `"[N target] over [planned duration]"` · In-Progress: `"[N collected] of [N target] ([%] complete)"` · Completed: `"[N total] over [actual duration]"` |
| Next Step | `[action] (Owner)` |

Rules:
- No "Experiment" row (that's the page title)
- No "Verdict" row (that's the banner)
- Confidence communicates, not calculates: "Medium — 5 ambassadors, directional only" not "P(B>A) = 0.87 via Beta-Binomial"

---

### 2. The Experiment

2-3 sentences, **50 words max**.

- Answers: what prompted this → what we're testing → what question it answers
- One number max (the headline context metric or baseline)
- No methodology, no caveats, no "DB-verified" flags
- Written for someone who has never seen this experiment
- Context (the "what prompted this") should be 1 number + 1 sentence: the bottleneck, gap, or failure rate that made this experiment necessary. Example: "78% of merchants never sell. Testing whether a small cash incentive closes the 0→1 gap." Do not reference prior experiment versions — state the problem directly.
- For Completed experiments: add what happened (one clause)

---

### 2.5. Design Brief (Intervention experiments only)

**When to use:** Any experiment where the treatment mechanics need to be understood before the decision criteria make sense. Use for: incentive tiers, message templates, training protocols, pricing structures. Skip for observation-only experiments.

**Format:** 1 compact table. Section title adapts:
- Incentive experiments → **"The Offer"**
- Messaging experiments → **"The Message"**
- Training experiments → **"The Protocol"**

**Rules:**
- 1 table max, 3–5 rows
- For incentives: Level | What Merchant/Person Does | Reward
- Include 1–2 footnote lines: what counts, what doesn't, delivery method
- If tiers stack or have a cap, state it in one line below the table
- No fraud rules, validity caveats, or cost models here — those go in toggles

---

### 3. Decision Criteria

**All states.** Pulled out of the Decision Contract toggle — visible to every reader.

**Format:**
1. A simplified 2-3 row table: Result → Verdict → plain-English Action (no stats jargon)
2. One plain-English criterion sentence: "If X happens, we'll Y."

Rules:
- No row colors in the Decision Criteria table — the text labels (SHIP IT / ITERATE / KILL IT) carry the signal. Colors create visual noise when the table is already readable.
- Row colors are reserved for Breakdown Detail (Layer 3) where color encodes tier or cohort performance at a glance across many rows.
- No MDE, no P-values, no Beta distributions in this section
- Each row must be a clear observable outcome, not a statistical threshold

---

### 4. Scale & Confidence

**All states.** Two components, **80 words max total**:

1. **Sample progress** — "X [collected/logged] of Y needed (Z% of target). At current pace, [on track for date / behind by N days]." For Planned: "We need X over Y days." For Completed: "X total over Y days."

2. **Validity + Actionability** — 1-2 sentences: state the design type in plain English, then say what findings will and won't support.
   - Observational: "Ambassadors chose their own hours — findings are directional. Enough to decide Phase 2; not enough to permanently restructure operations."
   - Controlled (RCT): "Randomly assigned — findings are causal. Sufficient to act."
   - Time-split: "Pre/post comparison — trends could explain part of any improvement."

Rules:
- No jargon: "statistical power" → "confident enough to act"; "MDE" → "the minimum difference we care about"; "confound" → "other factors that could explain the result"
- Use SUFFICIENT / WEAK / INSUFFICIENT as a 1-word header if helpful

---

### 5. Early Signals [In-Progress only]

Preliminary data. **Insight-first order** — the headline is the point; the table proves it.

**Structure (in this order):**
1. **Headline callout** — one bold sentence: the single most important thing the data shows so far. Mark *(preliminary)* at the end of the header. Color matches direction: blue = neutral/watch, yellow = caution, green = positive signal. Format: bold statement → *Evidence: [data]* → [implication in one line]

2. **One comparison table** — Baseline vs Current (side-by-side epochs). Even when current is still accumulating, the column structure must be present from day one. Use "—" for empty cells. Footer: *"Need X [visits] for confidence; Y logged so far (Day N/total)."*

   Required columns:
   | Window | Baseline visits | Baseline rate | Current visits | Current rate | vs. Target |

3. **One implication line** — plain prose, max 20 words: "→ [what this means for the decision when current data fills in]"

Cap: **1 headline callout + 1 table + 1 implication line.** No additional callouts.

---

### 6a. What Happens Next [In-Progress only]

Single sentence: "[Data collection action] by [Date]. [Who updates the page]."

Example: "Final L1/L2/L3 counts on Feb 28 once all windows close. Asharib updates this page with verdict."

Rule: The deadline belongs in the Scorecard (row 5) and here — NOT in the State Banner. The banner states the blocker; the Scorecard and this section state the timeline.

---

### 5. What We Found [Completed only]

Two components:

**One comparison table** (max 4 rows): before vs after, or treatment vs control. Mark metrics (observed) or (reported) inline.

**2-3 insight callouts** using the INSIGHT/Evidence/Implication format. Each insight gets a different-colored callout (blue, yellow, green). Goodhart checks, temporal stability, and heterogeneity findings become insights here — not a separate section.

Cap: **3 insights maximum.** If you have more, pick the 3 that change decisions.

---

### 6. What To Do Next [Completed only]

Numbered list, 3-5 items.

- Each item: **bold action** + context + (Owner)
- Feed-forward (next experiment proposal) is the last bullet, not a separate section
- No conditional trees — if the decision isn't made yet, say "Decide at [date] sync"

**Multi-part decisions** (e.g., pipeline + signals, multiple channels): use a mini decision table before the action list:

| Component | Verdict | Action |
|-----------|---------|--------|
| Pipeline (EOI→active) | SHIP (22%) | Scale to next cohort |
| Signal: Engagement | SHIP | Embed in flyer + interview |
| Signal: Communication | ITERATE | Needs larger sample |

---

### 7. Breakdown Detail (collapsed toggle)

Adapts by experiment type:

- **Funnel experiments**: per-ambassador table with tier labels (Reliable/Directional/Insufficient)
- **Hiring experiments**: per-channel or per-signal table
- **Incentive experiments**: per-tier or per-merchant-cohort table

Rules:
- Single consolidated table (pre + post as columns, not separate tables)
- Tier/color labels as colored row backgrounds
- Summary callout placed **ABOVE the toggle** (visible without expanding) with the pooled top-line result
- Section title adapts: "Per-Ambassador Detail" / "Channel Breakdown" / "Tier Breakdown"
- **Never show the same table in Layer 2 AND here.** The detailed version lives in this toggle; the summary lives in What We Found.
- **Tier data is required** whenever the dashboard computes per-recipient or per-ambassador tiers — include the full tier breakdown here even if the visible layer only references the aggregate. This is operational output that field leads need.

Tier definitions for ambassador breakdowns:
- **Reliable**: n ≥ 20
- **Directional**: 5 ≤ n < 20
- **Insufficient**: n < 5

---

### 8. How We Tested This (collapsed toggle)

Contains (~400 words total):
- **Context**: what prompted the experiment (1-2 paragraphs)
- **Formal hypothesis** (IF/THEN/BECAUSE) or research question
- **Design**: split type, treatment/control, duration
- **Assumption check** (5 questions, answered inline)
- **Statistical validity** table + verdict + any clustering/confound discussion

---

### 9. Decision Contract (collapsed toggle)

- **Decision Rules** table (3-4 rows, colored: green for SHIP IT, yellow for ITERATE, red for KILL IT)
- **Kill Criteria** table (3-4 rows)
- **Planned Actions** subsection [In-Progress only] — numbered list of actions pre-committed for when the experiment concludes. Owners assigned in advance.

---

### 10. Appendix (collapsed toggle)

- Raw data tables
- SQL queries used
- Methodology notes (Beta distributions, ICC, design effects — all the math lives here)
- Excluded data and rationale
- Baseline detail tables

---

## No-Redundancy Rule

- Verdict appears **ONCE** (banner)
- Primary metric baseline/result appears **ONCE** (scorecard)
- Never repeat the same data point across sections

---

## Writing Rules

### No Filler
Delete every sentence that doesn't add information. "It's worth noting that" → delete. "Interestingly" → delete. Just state the finding. If a section has nothing meaningful, write "No findings" — don't pad it.

### Specificity Standard
Every number needs a source: "(n=42, Feb 10-14 data)". Every claim needs evidence: "Demo rate increased" → "Demo rate increased from 7% to 48% (20/42)". Reject "improved" without magnitude. Reject "significant" without statistical test.

### Observed Over Reported
Always flag: (observed) = system/database data, (reported) = ambassador self-report. When they conflict, observed wins. Note the discrepancy — the gap between observed and reported is itself a finding.

### 50-Word Cap on The Experiment
Count words. If over 50, cut. Methodology and caveats belong in the toggle, not here.

### 1-Callout Cap on Early Signals
In-Progress pages: max 1 headline callout. It must include *(preliminary)* in the header. Treat as a hypothesis, not a finding.

### 3-Insight Cap on What We Found
Completed pages: if you have 4+ insights, pick the 3 that change decisions. The rest go in the Appendix.

### Toggle Test
"Can a non-data reader make the correct decision without this section?" If yes → it belongs in a collapsed toggle (Layer 3). If no → it stays visible (Layer 1 or 2).

### Denominator Rule
When citing a fraction, always use the full population denominator. If data coverage is partial, state coverage separately:
- ❌ "29/33 covered non-onboarded" (reader confuses 33 with a different cohort)
- ✅ "29/35 non-onboarded (83%). Amplitude coverage: 33/35."

### Selection Bias Rule
If any data source has known selection bias (e.g., ambassador only logs successes), report TWO rates:
- Comparable rate (excl. biased data) as the headline
- Pooled rate (incl. biased data) as a parenthetical
- ❌ "49% onboarding rate" (inflated by biased ambassador)
- ✅ "35% comparable (17/49, Arslan+Zahid), 49% pooled (33/68, incl. Owais selection bias)"

### No-Duplicate Table Rule
Never show the same table in Layer 2 and Layer 3. If a table appears in "What We Found," it does NOT appear in "Breakdown Detail." The detailed version lives in the toggle; the summary lives in Layer 2.

### Tier Data Rule
If the dashboard computes per-recipient or per-ambassador tiers, the Notion report MUST include the full tier breakdown in the Breakdown Detail toggle — even if the visible layer only references the aggregate. This is operational output that field leads need.

### Narrative Quality
Write for people who will skim. Bold the verdict, bold the key numbers. Use tables for comparison, prose for interpretation. One insight per callout. No compound insights.

### Plain Language in Layers 1-2

**Layer 1-2 (visible)**: No statistical jargon. No P values, Beta distributions, CI, MDE, ICC, power, priors/posteriors, credibility intervals. Replace with plain English: "Bayesian sequential monitor" → "daily comparison tracker"; "informative priors" → "pre-existing historical data"; "CIs non-overlapping" → "ranges don't overlap".

**Layer 3 (toggles)**: Jargon is acceptable but **must include a plain-English parenthetical on first use**. The reader may not have seen these concepts in months. Examples:
- "Beta(21, 470) prior" → "Beta(21, 470) prior (encoding 20 onboardings from 489 daytime visits — the more data, the narrower the range)"
- "P(Night>Day) > 0.95" → "P(Night>Day) > 0.95 (95% chance nighttime truly outperforms daytime)"
- "Informative priors" → "informative priors (using historical data as a starting point instead of starting from scratch)"
- "Sequential monitoring" → "sequential monitoring (checking results daily as data accumulates, instead of waiting until the end)"

**Test**: Read each sentence aloud. If someone who took one stats course 5 years ago would need to Google a term, add a parenthetical.

### Storytelling Frame
Executive summaries for syncs follow: what happened → what needs attention → what we learned. Every finding should answer "so what?" — if it doesn't change a decision, cut it. The audience is Turab and Brandon (CEO) — they care about decisions, not methodology.
