# EXP-012 Analysis Plan
## University Student Interview Research — From Raw Data to Final Presentation

**Experiment**: EXP-012 — University Student Growth Partner Interest Research
**Sample**: 186 students across 6 Karachi campuses
**Data Sources**: Google Form responses (gsheet) + Voice recordings (pending transcription)
**Objective**: Answer leadership's four questions — messaging, concerns, incentive structures, and whether to prioritize students

> **Discrepancy Note**: Transcription data may not perfectly match form responses — interviewers sometimes paraphrased or summarized in the form. The final version must reconcile form responses with actual spoken words.

---

## Build Log

### Round 0 — Initial HTML Build
Built `EXP-012-learnings.html` from form data analysis. Sections: Hero, Experiment (EXP-016 on Empirium), Direct Answers, Exec Summary, Demographics, Warm Up, Opportunity Reaction, Compensation, Identity, Quit/Join Signals, Learnings (6), Assumption Update, Decision, Recommendations (7), Cross-Tabs. All charts via Chart.js, animations via GSAP ScrollTrigger.

### Round 1 — Structural Fixes (Dex/Eric Critique, 12 items)
Addressed 12 structural issues from internal critique:
1. Added experiment framing section (hypothesis, success criteria, verdict grid, decision rules)
2. Added direct answers section (4 cards answering leadership's questions upfront)
3. Added preliminary data status badge + warning callout
4. Added falsifiability condition callout
5. Added trade-offs callout in recommendations
6. Added assumption confidence update section (before/after bars)
7. Added cross-tab analysis section (University × Follow-up, Gig × Follow-up stacked bars)
8. Added thematic coding methodology collapsible
9. Replaced generic "themes" with 6 structured learning cards
10. Added math box for compensation model
11. Added decision card with conditional PROCEED verdict
12. Added placeholder banners for pending transcription sections

### Round 2 — Presentation Polish (6 items)
Prepared for live call readability:
1. **Fixed "186%" bug** — Added `data-suffix=" "` to render "186" not "186%"
2. **Removed all "Brandon" mentions** — Replaced with "Direct Answers" / "Leadership"
3. **University classification cards** — 6-card grid below University Distribution chart with tier badges (ELITE/UPPER-MID/MID-TIER/PUBLIC/ACCESSIBLE), tuition in USD, one-liner, and per-university "Would join" conversion rate
4. **PKR → USD conversion** — All monetary values converted at 280 PKR/$. Single footnote near hero. Updated: stat cards, narratives, chart labels (income + earning), math box, verdict text, Direct Answers cards
5. **Text reduction for presentation** — All narratives → 1-2 bullet fragments, section-intros → 1 sentence max, learning cards → 2 sentences max, trade-offs/falsifiability/assumption callouts trimmed
6. **Sticky dot nav** — Fixed left-side navigation with 5 groups (Setup / Who / What They Said / What We Learned / What To Do). Appears after hero, highlights current section via ScrollTrigger, click-to-scroll, labels always visible (dim, brighten on active/hover), hidden on mobile

---

## Part 1: Google Sheet Response Analysis

### 1.1 Categorical Columns — Direct Frequency Counts (13 columns)

| Column | Field | Type | Status |
|--------|-------|------|--------|
| 3 | University / Campus | 6 campuses | ✅ Done — charted + classification cards |
| 5 | Age | Numeric (18-35) | ✅ Done — charted |
| 6 | Gender | M/F/Other | ✅ Done — charted |
| 9 | Smartphone Type | Android/iPhone | ✅ Done — charted |
| 10 | Approximate Monthly Income | 5 brackets | ✅ Done — charted in USD |
| 11 | Prior Gig / Freelance Work? | Yes/No | ✅ Done — charted |
| 12 | How Did You Find This Interviewee? | 4 options | ✅ Done |
| 18 | Shop comfort feeling | Excited/Open/Hesitant/Against | ✅ Done — charted |
| 19 | Volume perception (30-40 visits) | Easy/Doable/Hard/No way | ✅ Done — charted |
| 21 | Preferred pay structure | 4 options | ✅ Done — charted |
| 22 | Base+bonus appeal | 3 options | ✅ Done — charted |
| 28 | Interest Level (interviewer) | High/Medium/Low | ✅ Done — charted |
| 29 | Comfort with Shop Visits (interviewer) | Natural/Hesitant/Uncomfortable | ✅ Done — charted |
| 30 | Follow-up Likelihood (interviewer) | Would join/Maybe/Unlikely | ✅ Done — charted |

### 1.2 Free-Text Columns — Thematic Coding (8 columns)

| Column | Field | Coding Approach | Status |
|--------|-------|----------------|--------|
| 16 | First reaction | Sentiment + theme (Positive/Curious/Neutral/Hesitant/Negative) | ✅ Done — charted |
| 17 | Questions asked | Topic clustering (Pay/Process/App/Time/Safety/Area/Growth/Training) | ✅ Done — charted |
| 23 | Identity framing | Category mapping (Side hustle/Job/Business/Part-time/Freelance/Internship) | ✅ Done — charted |
| 24 | Preferred title | Normalize to standard options + custom titles | ✅ Done — charted |
| 25 | Quit signals | Theme extraction (10 themes) | ✅ Done — signal list with counts |
| 26 | Join signals | Theme extraction (8 themes) | ✅ Done — signal list with counts |
| 27 | Other notable things | Qualitative review for standout insights | ✅ Done |
| 31 | Notable quotes | Curate top 10-15 for presentation | ✅ Done — 6 quotes placed in report |

### 1.3 Numeric Columns — Distribution Analysis (3 columns)

| Column | Field | Analysis | Status |
|--------|-------|----------|--------|
| 5 | Age | Distribution, mean, median, buckets | ✅ Done |
| 20 | Minimum monthly earning | Bucket distribution, mean/median (converted to USD) | ✅ Done |
| 0 | Timestamp | Collection timeline, response rate by day | Deferred |

### 1.4 Cross-Tabulation Matrix (Priority Cross-Tabs)

| Cross-Tab | Why It Matters | Status |
|-----------|---------------|--------|
| University × Follow-up Likelihood | Which campuses have the highest-quality leads? | ✅ Done — stacked bar in HTML |
| Prior Gig × Follow-up Likelihood | Does experience predict conversion? | ✅ Done — stacked bar in HTML |
| Gender × Shop Comfort | Do women feel less comfortable with field visits? | Pending |
| Income × Minimum Earning | Do students with income have higher expectations? | Pending |
| Age × Volume Perception | Are younger students more optimistic about workload? | Pending |
| University × Pay Structure | Do different campuses prefer different comp models? | Pending |
| Interest Level × Follow-up Likelihood | How well does interest predict actual intent? | Pending |
| Gender × Preferred Title | Do title preferences differ by gender? | Pending |
| Prior Gig × Identity Framing | Do experienced students frame it differently? | Pending |
| Smartphone × University | Android/iPhone distribution by campus (operational) | Pending |

---

## Part 2: Voice Recording Transcription Analysis

**Status**: Not started — pending transcription of 186 voice recordings

### 2.1 Transcription Preparation & Segmentation
- Transcribe all voice recordings (186 interviews × ~8-10 min each)
- Segment transcriptions by interview section (Warm Up / Opportunity / Compensation / Identity / Closing)
- Match each transcription to its corresponding form response row
- Flag any discrepancies between transcribed content and form responses

### 2.2 Thematic Coding Framework Per Interview Section

**Section 1 — Warm Up**:
- Current earning activities (detailed categories)
- Side hustle experience types
- Academic vs. earning priority framing

**Section 2 — Opportunity Reaction**:
- Emotional tone (excitement spectrum)
- Specific concerns raised (verbatim vs. interviewer summary)
- Shop visit comfort — verbal cues vs. categorical response
- Analogies/comparisons students make ("like an internship", "like Uber")

**Section 3 — Compensation**:
- Pay reasoning (why they chose that number)
- Risk tolerance language
- Comparison anchors (what they compare this earning to)
- Negotiation signals

**Section 4 — Identity**:
- Self-framing language
- Social status concerns
- Peer perception awareness
- Title reasoning (why they prefer what they chose)

**Section 5 — Closing**:
- Quit signal specificity and emotional weight
- Join signal enthusiasm level
- Unsolicited suggestions/ideas
- Body language / tone cues noted by interviewer

### 2.3 Sentiment Analysis
- Per-interview overall sentiment score (1-5)
- Per-section sentiment tracking (does it increase or decrease through the interview?)
- Identify "turning points" — where skeptics became interested or interested students became hesitant

### 2.4 Quote Extraction
- 3-5 standout quotes per section (15-25 total for the final report)
- Selection criteria: memorable, representative, actionable
- Include student name, university, and context for each quote

### 2.5 Language & Framing Analysis
- Urdu vs. English usage patterns
- Business vocabulary level
- Self-efficacy language ("I can" vs. "I'm not sure I can")
- Social framing ("my friends would think" / "my parents would say")

---

## Part 3: Segment Analysis (Personas)

**Status**: Not started — requires transcription data

### 3.1 Persona Identification Via Clustering
Using cross-tab data + transcription themes, identify 3-5 distinct student personas:

**Hypothesized personas** (to be validated):
1. **The Hustler** — Prior gig experience, excited, performance-pay, sees it as a business
2. **The Cautious Earner** — No gig experience, open but hesitant, prefers fixed pay, worried about rejection
3. **The Not-Interested** — Low interest, uncomfortable with shops, high earning expectations, unlikely to join
4. **The Career Builder** — Sees it as an internship/experience, interested in growth path, analytical questions
5. **The Social Influencer** — Excited about the people aspect, would recruit friends, cares about team environment

### 3.2 Per-Persona Profiles
For each persona:
- Size (% of sample)
- Key demographics
- Messaging that resonates
- Concerns to address
- Recommended incentive structure
- Conversion probability
- Recommended approach

---

## Part 4: Final HTML Compilation

### 4.1 Current HTML State (Post Round 2)

| HTML Section | Current State | What Transcription Adds |
|-------------|---------------|------------------------|
| Hero | Complete — animated title, meta, USD footnote | — |
| Experiment (00) | Complete — hypothesis, criteria, verdict, decision rules | — |
| Direct Answers (00B) | Complete — 4 cards, USD values, concise | Persona-specific nuance |
| Exec Summary (01) | Complete — 4 stat cards (USD), bullet narrative | — |
| Demographics (02) | Complete — stat cards, 6 charts, university classification grid with tier badges | — |
| Warm Up (03) | Form-based stats + placeholder | Deeper side hustle themes, earning motivations |
| Opportunity Reaction (04) | 4 charts + bullet narrative + placeholder | Sentiment curves, verbatim reactions, analogies used |
| Compensation (05) | 4 charts + USD math box + placeholder | Pay reasoning, risk tolerance framing |
| Identity (06) | 2 charts + bullet narrative + placeholder | Self-framing language, social status concerns |
| Quit/Join Signals (07) | Signal lists + 2 charts + placeholder | Emotional weight, enthusiasm levels, curated quotes |
| Learnings (08) | 6 structured learning cards (concise) + methodology | Transcription-validated refinements |
| Assumption (09) | Confidence before/after bars + what-moves-higher | — |
| Decision (10) | PROCEED (conditional) card + falsifiability | May be modified by transcription findings |
| Recommendations (11) | 7 recs + trade-offs + USD math box | Persona-specific messaging playbooks |
| Cross-Tabs (12) | 2 stacked bar charts + bullet narrative | Additional cross-tabs from pending list |
| Dot Nav | Complete — 5 groups, sticky left, scroll-tracked | — |

### 4.2 Charts Implemented (18 total)

1. University Distribution (bar)
2. Gender Split (donut)
3. Age Distribution (bar)
4. Current Monthly Income (horizontal bar, USD labels)
5. Prior Gig Experience (donut)
6. Smartphone Type (donut)
7. First Reaction (horizontal bar)
8. Shop Visit Comfort (donut)
9. Questions Asked (horizontal bar)
10. Interest Level (donut)
11. Volume Perception (bar)
12. Earning Expectation (bar, USD labels)
13. Pay Structure Preference (bar)
14. Base+Bonus Appeal (donut)
15. Identity Framing (horizontal bar)
16. Preferred Title (bar)
17. University × Follow-up (stacked bar)
18. Prior Gig × Follow-up (stacked bar)

### 4.3 Charts Still Needed for Final Version
- Persona distribution donut chart
- Sentiment arc chart (average sentiment by interview section)
- Cross-tab heatmaps for remaining priority cross-tabs
- Follow-up Likelihood (donut) — currently in Quit/Join section
- Comfort with Shop Visits interviewer assessment (donut)

### 4.4 Quote Integration Plan
- Each content section: 1-2 pull quotes in styled callout boxes (6 placed so far)
- Quit/Join section: Quote pairs (contrast format)
- More quotes needed from transcription phase

---

## Part 5: Mapping to Leadership's Questions

Leadership asked four specific questions:

### 5.1 "What messaging works for students"
- **Form data** ✅: First reaction themes, questions asked, identity framing → "side hustle" framing, lead with $125–179/mo earning potential
- **Transcription** (pending): Exact language that resonated, analogies that worked, how interviewers adapted
- **Final answer**: Per-persona messaging playbook

### 5.2 "Concerns"
- **Form data** ✅: Quit signals (coded), shop comfort levels, volume perception → time conflicts #1, rejection anxiety #3, pay uncertainty
- **Transcription** (pending): Specific concern language, emotional intensity, concerns not captured in form
- **Final answer**: Ranked concern list with mitigation strategies

### 5.3 "Incentive structures"
- **Form data** ✅: Pay structure preference, base+bonus appeal, minimum earning distribution → hybrid comp $54–71 base + $7–11/merchant
- **Transcription** (pending): Pay reasoning, comparison anchors, negotiation signals
- **Final answer**: Recommended tiered compensation model with rationale

### 5.4 "Whether to prioritize this group"
- **Form data** ✅: All 3 success criteria met → PROCEED (conditional). 37% would join, 72% comfortable, median $143
- **Transcription** (pending): Quality of engagement, genuine vs. polite interest, conversion signals
- **Final answer**: Yes — selectively. IBA + Habib first, over-index on gig-experienced students
- **Falsifiability**: If ≥40% of "Would join" show weak verbal commitment in transcription, decision shifts to ITERATE

### 5.5 Executive Summary
- **Current**: Complete with bullet-point format, 4 key stat cards, conditional PROCEED
- **Final**: Will add persona-specific targeting, campus-level rollout plan, refined conversion estimates

---

## Appendix: Column Reference

```
[0]  Timestamp
[1]  Email Address
[2]  Your Name (Interviewer)
[3]  University / Campus
[4]  Interviewee First Name
[5]  Age
[6]  Gender
[7]  Major / Program
[8]  Semester / Year
[9]  Smartphone Type
[10] Approximate Monthly Income
[11] Prior Gig / Freelance Work?
[12] How Did You Find This Interviewee?
[13] What do they study and what year?
[14] Do they currently earn money? How?
[15] Have they tried any side hustles before?
[16] What was their first reaction?
[17] What questions did they ask?
[18] How did they feel about going into shops?
[19] How do they feel about doing 30-40 shop visits in 2 weeks?
[20] Minimum monthly earning to make this worth their time?
[21] Preferred pay structure?
[22] If the base salary was lower but you could earn more per sign-up, would that appeal?
[23] What would they call this — job, side hustle, business, or something else?
[24] Preferred title?
[25] What would make them quit after the first week?
[26] What would make them tell 5 friends to join?
[27] Any other notable things they said?
[28] Interest Level
[29] Comfort with Shop Visits
[30] Follow-up Likelihood
[31] Notable Quotes
```
