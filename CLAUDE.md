# Ground Force Experiments

Standalone experiment tracking for Zar's ground force (field ambassador) team. Each subdirectory is one experiment.

## Conventions

**Session hygiene:** After approximately 30 turns in a conversation, remind the user to start a fresh session or use `/compact` to reduce context size and save tokens. Say something like: "We're at ~30 turns — consider starting a fresh session or running /compact to keep token usage lean."

**Model usage:** Use Sonnet for routine tasks (simple searches, straightforward edits, boilerplate generation). Reserve Opus for complex reasoning, architectural decisions, and multi-step problem solving.

**Output rules:** Always show the full pipe table and insights output to the user (do not suppress or summarize). This applies to all Pattern A experiments.

**Experiment reports:** All experiment reports live on Notion (Experiment Tracker database). `Experimentation-OS.md` defines the report structure and writing rules. The **Helix** agent (`.claude/agents/helix.md`) manages the full experiment lifecycle: draft, design, plan, run, analyze, present. Invoke with `claude --agent helix`.

Key principles: lead with verdict (SHIP IT / ITERATE / KILL IT / NEEDS MORE DATA), include statistical validity check, use INSIGHT/Evidence/Implication format, prefer observed metrics over self-reported.

## Architecture Patterns

### Pattern A: Sheet-Based Funnel

Fetches data from a Google Sheet, computes funnel metrics, prints terminal tables, and generates an HTML report.

**DAG** (no circular deps):
```
config  ←  data  ←  funnel  ←  output
                       ↑
                   flowchart
                       ↑
                     run.py
```

**Standard files:**

| File | Purpose |
|------|---------|
| `run.py` | Single entry point |
| `config.py` | Experiment constants: name, dates, sheet ID, column names |
| `data.py` | Fetch sheet + parse timestamps + row classifiers |
| `funnel.py` | Pure computation: metrics, nodes, ambassador breakdown |
| `output.py` | All terminal printing: tables + insights |
| `flowchart.py` | Generate HTML report (cards, charts) |
| `*.html` | Generated artifact (overwritten each run) |

**Run:** `cd <dir> && python3 run.py`

### Pattern B: SQL + Cache Assembly

Assembly pattern: `shell.html` + `style.css` + `app.js` → single self-contained HTML via string injection.

**Standard files:**

| File | Purpose |
|------|---------|
| `run.py` | Entry point: reads cache JSON, assembles HTML |
| `queries.py` | SQL queries (canonical source of truth for Rube MCP) |
| `ui/shell.html` | HTML skeleton with injection markers |
| `ui/style.css` | All CSS |
| `ui/app.js` | Client-side rendering, filters, interactivity |
| `*.html` | Generated artifact (overwritten each run) |

**Run:** `cd <dir> && python3 run.py --json <path-to-cache.json>`

### Pattern C: Markdown Only

Design doc / experiment brief living in a single `.md` file. No code, no generated artifacts.

## Experiment Catalog

| ID | Directory | Pattern | Split | What it tests |
|----|-----------|---------|-------|---------------|
| EXP-001 | `show-dont-tell/` | A | Time-based (baseline vs experiment) | Demo-first opener vs verbal pitch |
| EXP-002 | `social-proof-map/` | A | Person-based (staggered multi-ambassador) | Showing nearby-merchant map at opener |
| EXP-006 | `question-redirect/` | A | Time-based (pre- vs post-training) | Universal redirect phrase for Q→Demo |
| — | `merchant-user-onboardings/` | B | N/A (dashboard) | Merchant onboarding, activation, retention |
| EXP-001+ | `demo-dollars-usage/` | B | N/A (cohort analysis) | What demo-dollar recipients did with $5 |
| EXP-007 | ↳ folded into above | B | N/A (retrospective) | 7-day post-demo merchant transactions |
| EXP-008 | `gold-market-research/` | C | Round-based discovery (R1: Rawalpindi, R2: Islamabad) | Merchant demand for digital gold + jeweler markup argument |
| EXP-009 | `directed-day/` | B | Time-based (autonomous vs directed) | Structured daily task lists with geo-clustered visits |
| EXP-010 | Notion-only | C | N/A (observation) | Shadow top/mid/bottom ambassadors to explain Q-to-Demo variance |
| EXP-011 | Notion-only | C | Time-based (before/after WhatsApp SOP) | WhatsApp follow-up within 2h of demo |
| EXP-012 | Notion-only | C | Time-based (before/after info shot) | Preemptive 15s "how it works" explanation |
| EXP-013 | Notion-only | C | N/A (discovery) | BD market structure mapping: 30 agent interviews |
| EXP-014 | Notion-only | C | N/A (infrastructure) | BD tracking infrastructure: forms, GPS, timezone |
| EXP-015 | Notion-only | C | Person-based (within-ambassador A/B) | BD pitch A/B: savings vs remittance framing |
| EXP-016 | Notion-only | C | N/A (analysis) | Cross-market PK vs BD funnel benchmark |
| EXP-017 | Notion-only | C | Person-based (3 pools × 3 candidates) | PK hiring tournament: EP/JC agents vs students vs merchants |
| EXP-018 | Notion-only | C | N/A (analysis) | Top performer DNA profiling (r > 0.5 threshold) |
| EXP-019 | Notion-only | C | Person-based (referral vs pipeline) | Referral hiring: top-performer referrals vs EXP-017 pipeline |

## Experiments

### Show Don't Tell (EXP-001)

Tests a new opener strategy where ambassadors demonstrate the app instead of pitching verbally. Started Feb 10, 2026. Outputs: baseline vs experiment funnel comparison, per-ambassador breakdown, and updates `dont_show_tell_exp.html`.

### Social Proof Map (EXP-002)

Tests whether showing a map of nearby ZAR merchants bypasses objections at the opener stage. Person-based split with staggered start dates: Phase 1 (Feb 11-15, Sharoon only) -> Phase 2 (Feb 16+, Sharoon + Afsar + Arslan). Control = all non-map ambassadors + map ambassadors' pre-start data. Outputs: Map Group vs Control funnel comparison, per-ambassador breakdowns for both groups, friction vs credibility analysis, and generates `social_proof_map.html` with 5 cards.

**Experiment card:** `exp-002-social-proof-map.md` — full hypothesis, decision rules, kill criteria, phase design, statistical validity (verdict: WEAK for Phase 1, Phase 2 expansion required).

**Config extras:** `MAP_AMBASSADORS` dict mapping ambassador names to their map start dates (replaces single `TARGET_AMBASSADOR`). No fixed end date — uses today. `data.py` `split_by_group()` handles per-ambassador staggered starts. No `QuestionDropoffData` or `DayOnDayProgression` — simpler `funnel.py` (~90 lines vs 220).

**Key design decisions:** Afsar/Arslan's pre-Feb 16 data is valid control data (their own baseline). Phase 2 answers: is the map effect method-driven (transfers across ambassadors) or person-driven (Sharoon-specific)? SHIP requires E2E >= 15% AND consistent effect across 2+ ambassadors.

### Question Redirect Protocol (EXP-006)

Follow-up to EXP-001. Tests whether training ambassadors to redirect merchant questions into immediate app demos improves Q→Demo conversion. EXP-001 revealed the mid-funnel bottleneck: 73% of question-askers (69/95) never saw a demo. Top dropoff questions (Company Info, How It Works, Trust & Safety) are all better shown than explained. Training-based split: pre-training (Feb 10-15) vs post-training (Feb 16+). Rigorous redirect training started Feb 16, 2026.

**Experiment card**: `exp-006-question-redirect.md` — full hypothesis, decision rules, kill criteria, statistical validity check (verdict: WEAK due to 5 ambassador clusters and no compliance verification).

**Key design decisions**: Baseline 25% Q→Demo (43/172, Feb 10-15). Target 50% aspirational, 45% SHIP threshold. Confirmation metric: E2E onboarding rate. Ambassador-stratified analysis (each ambassador as own control). Decision requires ≥4/5 ambassadors improving AND pooled ≥45% to SHIP. SHIP action: Qasim retrains all ambassadors + Daniel builds into in-app playbook.

**Metrics:** `QDemoMetrics` (not `FunnelMetrics`), `TopicConversion` for per-question rates. Outputs: Q→Demo before/after comparison, per-topic conversion rates, per-ambassador Q→Demo rates, and generates `question_redirect.html` with 3 cards (comparison, per-question conversion, ambassador breakdown).

### Network Growth Through Merchants

Tracks merchant-user onboardings, activation, transacting users, and merchant retention. Self-contained HTML one-pager with interactive date picker, city filter, sortable tables, and Chart.js retention chart.

**Earnings model** — two incentive tiers based on onboarding date:
- **Tier 1** (Jan 1 – Jan 27, 2026): $1.00 per user onboarded
- **Tier 2** (Jan 28, 2026+): $0.50 per user onboarded + $0.50 per activated user

`earnings = (tier1_onboarded × $1.00) + (tier2_onboarded × $0.50) + (tier2_activated × $0.50)`

**Data source:** Reads `merchant_summary` and `merchant_retention` arrays from cache JSON. `queries.py` contains SQL with tier-split earnings CTEs. `app.js` handles JS rendering, filters, calendar, earnings computation.

### Demo Dollars Usage (EXP-001 extension + EXP-007)

Traces what non-onboarded recipients did with the $5 demo cash notes ambassadors gave them. Identifies who "understood the product" enough to be worth revisiting. Self-contained HTML one-pager with 8 story cards.

**Unique UI classes:** `.recommendation-box`, `.insight-box`, `.amount-table` in `style.css`. `app.js` handles client-side rendering, scoring, story cards, timing analysis.

#### Iterations

| Iter | What was added |
|------|----------------|
| 1 | Story cards, non-onboarded scoping, recipient detail table |
| 2 | Better identifiers (names, phone), secured account check |
| 3 | Cycling redefinition (full round-trip only), ambassador breakdown |
| 4 | Timing analysis ("When Do They Act?"), amount effectiveness ("Is $5 the Right Amount?"), "Days to Act" detail column, Amplitude app opens data |
| 5 | Brand recall analysis (timestamped app opens, 2h+ = brand recall), hours precision (timing card), executive summary, self-serving report (inline definitions, Terra communication principles) |
| 6 | Visit sheet enrichment (shop names + geocoordinates from Google Sheet), Location column in Revisit Targets with Google Maps links, CSV download button |
| 7 | EXP-007 post-demo transaction tracking: `demo_merchant_transactions_query()`, `time_to_first_tx_query()`, activation card with tx type breakdown and timing distribution |

#### "Understands the Product" Definition

Binary classification: demonstrated active use of at least one core product capability beyond passive receipt, excluding cycling back to the ambassador.

**Qualifying actions** (any one = understood): sent cash note to non-ambassador, card purchase, bank transfer, ZCE order.

**Excluded**: receiving $5 (passive), holding balance (passive), sending $5 back to ambassador (cycling — Nash anti-fraud filter).

#### Timing Analysis (Iteration 4)

`recipient_timing_query()` finds each recipient's first qualifying activity timestamp. Uses per-type first-timestamp CTEs (CN send, card, BT, ZCE) → `union all` → `row_number()` to pick earliest. Uses `claimed_at` (full timestamp) as t=0.

Key finding: median time to first activity is ~43 minutes. 100% of engaged recipients act within 24 hours. Revisit rule: check after 1 day, give up after 2.

#### Visit Sheet Enrichment (Iteration 6)

`recipient_overview` entries can be enriched with `business_name`, `location_lat`, and `location_lng` from the ambassador visit log Google Sheet (`1bFf0NAQFFXIYYxMC1yJeqowRz6MwT_-xawZeg5H9wUQ`, tab "Form Responses 1"). Matching is done on normalized phone number (strip non-digits). Only updates `business_name` where currently null. The Revisit Targets table shows a "Location" column with clickable Google Maps links and a "Download CSV" button.

#### EXP-007: Post-Demo Merchant Transactions

Observational study — tracks 7-day post-demo transaction activity for EXP-001 demo recipients. No intervention, retrospective cohort analysis. Added `demo_merchant_transactions_query()` and `time_to_first_tx_query()` to `queries.py`, `renderExp007()` to `app.js`, and an EXP-007 card (activation funnel, tx type breakdown, time-to-first-tx histogram) to `shell.html`.

#### Data Source

Reads `recipient_overview`, `note_distribution`, `recipient_activity`, `ambassador_summary`, `app_opens`, `recipient_timing`, `app_opens_detailed`, `merchant_transactions`, and `time_to_first_tx` arrays from a cache JSON file. The `queries.py` file contains the canonical SQL for fetching this data via Rube MCP (Metabase database ID 1). App opens data is sourced from Amplitude (see Rube MCP notes below). `app_opens_detailed` contains per-event timestamps with `hours_after_demo` for brand recall analysis (Iteration 5).

### Digital Gold Market Research (EXP-008)

Discovery research (Pattern C) in `gold-market-research/exp-008-digital-gold.md`. Tests whether latent merchant demand exists for selling digital gold in Pakistan, with the jeweler markup savings argument (10-15% premium elimination) as the centerpiece pitch.

**Classification**: Discovery research, not an intervention experiment. Sequential round-based design: Round 1 (14 Rawalpindi interviews, completed Feb 12, 2026) → Round 2 (20 Islamabad EP/JC shops, planned). Round 1 data and analysis live at [gold-research.pages.dev](https://gold-research.pages.dev).

**Key design decisions**: Tiered signal framework replaces single "strong interest rate" — behavioral signals (unprompted actions) > economic argument (Q4 sentiment shift at markup pitch) > distribution willingness (Q6) > 48-hour callback confirmation (pickup → recall → WhatsApp micro-commitment). Pakistani shopkeeper hospitality ("haan bhai") is explicitly treated as noise floor, not signal. Decision rules: present findings with recommendation to leadership (Turab/Brandon). Signal matrix evaluation: 3-4 green = PROCEED, 2 green = ITERATE, 0-1 green = SHELVE.

**Round 1 findings**: 8/14 preferred dollars, 4/14 gold (29%). Top barrier: physical possession anxiety (4 mentions). Critical gap: jeweler markup advantage (Rs. 50-80K/tola savings) was never mentioned. Round 2 tests this as the centerpiece argument via sequential sentiment funnel (Q3 baseline → Q4 premium → Q5 redemption → Q6-Q8 distribution).

### Directed Day (EXP-009)

Tests whether structured daily task lists improve onboarding conversion and merchant reactivation. Ambassadors receive 8 geo-clustered visits per day (mix of onboarding revisits to demoed-not-onboarded merchants + reactivation visits to 14-day-inactive merchants) with geofenced verification at 200m.

**Run:** `cd directed-day && python3 run.py --json targets_cache.json` (dashboard) or `python3 run.py --json targets_cache.json --generate` (generate routes + dashboard)

**Architecture:** Pattern B hybrid with two-layer geo-clustering.

| File | Purpose |
|------|---------|
| `exp-009-directed-day.md` | Experiment card with hypothesis, decision rules, data |
| `queries.py` | SQL: reactivation targets (14d inactive), onboarding status check, outcome tracking |
| `task_generator.py` | Two-layer geo-clustering: zones (Layer 1) → daily routes (Layer 2) |
| `run.py` | Entry point: generate routes and/or assemble HTML dashboard |
| `ui/shell.html` | HTML skeleton with 4 cards |
| `ui/style.css` | Zar theme CSS |
| `ui/app.js` | Client-side: pool overview, zone map, route cards, outcome tracking |

**Key design decisions:**
- **Two-layer clustering**: Standard k-means with fixed cluster size degrades walkability (50% of clusters span 5-11km). Layer 1 creates tight geographic zones (≤2km radius, variable size). Layer 2 composes exactly 8 visits per ambassador from adjacent zones daily.
- **14-day rolling inactivity**: Reactivation targets are merchants with no ZCE (as fulfiller) or CN (as depositor) in last 14 days. Pool replenishes naturally.
- **Onboarding targets**: From visit sheet — merchants who got a demo (Golden Flow Amount set) but didn't onboard (QR Setup not done), filtered to those with GPS coordinates.
- **Karachi pool**: 130 merchants (76 onboarding + 54 reactivation). At 24 directed visits/day (3 ambassadors × 8), covers full pool in ~5.4 days.

**Companion app** (separate repo): Asharib will vibe-code a PWA for task list delivery with geofenced check-in, similar to agent-app.

### Pending Experiments (EXP-010 — EXP-019)

Ten experiments pending internal approval on Notion. All Pattern C (Notion-only experiment cards).

#### Pakistan Pitch & Training

- **EXP-010: Demo Shadow** — Qasim shadows top/mid/bottom ambassadors to explain 10-100% Q-to-Demo variance. Informs training vs hiring filter investment.
- **EXP-011: WhatsApp Follow-Up** — WhatsApp template within 2h of demo to improve demo-to-onboard from ~24% baseline. Parent: EXP-007.
- **EXP-012: Preemptive Pitch** — Preemptive 15s "how it works" explanation to increase demo rate from 25% baseline. Parent: EXP-006.

#### Bangladesh Market Entry

- **EXP-013: Market Structure Mapping** — 30 structured interviews across 3 Dhaka zones testing remittance vs savings resonance. Adapted from EXP-008 methodology.
- **EXP-014: Tracking Infrastructure** — Visit form, GPS, timezone (UTC+6), ambassador IDs for Bangladesh data collection.
- **EXP-015: Pitch A/B** — Savings-framed vs remittance-framed opener. Within-ambassador design, 120 visits, alternating neighborhoods.
- **EXP-016: Cross-Market Benchmark** — PK vs BD funnel comparison for Go/No-Go decision. Key metric: cost-per-active-merchant.

#### Hiring & Recruitment

- **EXP-017: Hiring Tournament PK** — 3 pools × 3 candidates in Pakistan (EP/JC agents, students, existing merchants). 5-day trial.
- **EXP-018: Top Performer DNA** — Profile all 8 current ambassadors to identify pre-hire traits predicting performance (r > 0.5 threshold).
- **EXP-019: Referral Hiring** — Top performers (Irfan, Junaid, Arslan) each refer 2 candidates. Benchmark against EXP-017 pool winners.

## Data Infrastructure

### DB Schema

#### Ambassador ID → Name Mappings

| User ID | Username | Real Name |
|---------|----------|-----------|
| `019bfeae-4ab6-77ef-8fe5-7fb91c7755ce` | `user_1ef1d1ea` | Arslan Ansari |
| `019c22a1-07a6-7c67-889e-5c655fe8ae11` | `owaisferoz1` | Owais Feroz |
| `a9519a82-c510-4b5b-a24b-ecec3f68de23` | `muhammadzahid` | Muhammad Zahid |

#### Schema Facts

- No `shops` table exists — use `merchant_onboarding_submissions` for business info
- `merchant_onboarding_submissions` has `business_name`, `phone_number`, `status` columns
- `users` table has `phone_number`, `username`, `first_name`, `last_name`, `email`
- "Secured account" = has at least one contact method (email or phone) on file:
  ```sql
  (u.email is not null and u.email != '')
  or (u.phone_number is not null and u.phone_number != '')
  ```
- PostgreSQL does NOT support `min()` on UUID type — must cast: `min(col::text)::uuid`
- No session/event/analytics tables in the database — app open data lives only in Amplitude
- Transaction types: `Transaction::CardSpend`, `Transaction::BankTransfer` (status = 3 for completed)
- ZCE orders: `zar_cash_exchange_orders` table, `initiator_id` for user, `status = 'completed'`
- Cash notes: `digital_cash_notes` table, `depositor_id` = sender, `claimant_id` = receiver, `status = 'claimed'`
- PKT time offset: `+ interval '5' hour` for UTC → Pakistan Time
- `product_enrollments`: `user_id` (FK to users.id), `state` (0=available, 1=onboarding, 2=enabled, 3=disabled), `product_definition_id` (FK), `created_at`
- `product_definitions`: `code` column, merchant code = `'zar_cash_exchange_merchant'`
- Since Dec 13 (SHIP-2069), new merchants use `product_enrollments` instead of `merchant_onboarding_submissions`. All merchant queries UNION both sources (MOS + PE). Zero overlap between the two populations.

#### Shared CTE Pattern

All demo dollars queries share two CTEs defined in `queries.py`:
- `_ambassadors_cte()` — users with ambassador role, excluding `EXCLUDED_IDS`
- `_demo_dollars_cte()` — cash notes from ambassadors to same-day-created recipients (Feb 1+), no amount filter

### Rube MCP (Composio)

#### Metabase (SQL Queries)
- Tool: `METABASE_POST_API_DATASET` with `database: 1`, `type: "native"`, `native: {query: "..."}`
- Connection is active and works via both `RUBE_MULTI_EXECUTE_TOOL` and workbench
- Session ID: `"each"` (pass in all subsequent meta tool calls)

#### Amplitude (App Analytics)
- Tools: `AMPLITUDE_FIND_USER` (UUID → amplitude_id), `AMPLITUDE_GET_USER_ACTIVITY` (event stream)
- **Critical**: These tools FAIL via `RUBE_MULTI_EXECUTE_TOOL` (routes to `api2.amplitude.com` which is the ingestion API, returns 404)
- **Workaround**: Use `run_composio_tool()` inside `RUBE_REMOTE_WORKBENCH` — this routes correctly and works
- Workflow: batch `AMPLITUDE_FIND_USER` to get amplitude_ids → batch `AMPLITUDE_GET_USER_ACTIVITY` to get events → count `session_start` events for app opens
- Event types for app opens: `"app_open"`, `"session_start"`, `"[Amplitude] Start Session"`, `"App Open"`, `"app_opened"`
- 28 of 32 demo dollar recipients were found in Amplitude (4 never opened the app at all)

#### Cache JSON Workflow

1. Write/update SQL in `queries.py` (canonical source of truth)
2. Run query via `METABASE_POST_API_DATASET` → extract `rows` from `data.data.rows`
3. Map column names from `data.data.cols[].name` to build JSON objects
4. For Amplitude data: batch via `RUBE_REMOTE_WORKBENCH` using `run_composio_tool()`
5. Update local `*_cache.json` file with new/updated arrays
6. Run `python3 run.py --json *_cache.json` to regenerate HTML

### Glossary

**Nash**, **Terra**, and **Atlas** are agents in the Praxis repository (`/Users/asharib/Documents/GitHub/praxis/`):
- **Nash** — Game theory expert. Designs incentive systems where fraud is economically irrational using mechanism design, auction theory, and Nash equilibria. Stress-tests systems for exploits.
- **Terra** — Field sales expert and Ground Force coach. Stress-tests ambassador training materials and pitch flows by simulating real merchant/ambassador personas before they ship.
- **Atlas** — Data navigator. Writes SQL queries and retrieves insights from the ZAR database. Uses a Five Questions Framework (metric, entity scope, time, grouping, output format) before writing any query.
