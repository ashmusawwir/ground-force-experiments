# Ground Force Experiments

Standalone experiment tracking for Zar's ground force (field ambassador) team. Each subdirectory is one experiment.

## Conventions

**Session hygiene:** After approximately 30 turns in a conversation, remind the user to start a fresh session or use `/compact` to reduce context size and save tokens. Say something like: "We're at ~30 turns — consider starting a fresh session or running /compact to keep token usage lean."

**Model usage:** Use Sonnet for routine tasks (simple searches, straightforward edits, boilerplate generation). Reserve Opus for complex reasoning, architectural decisions, and multi-step problem solving.

**Output rules:** Always show the full pipe table and insights output to the user (do not suppress or summarize). This applies to all Pattern A experiments.

**Percentage formatting:** All percentages use 2 significant digits via `_sig2()` helper. Terminal `output.py` and HTML `flowchart.py` must both use this function. Example: `18%` not `18.0%`, `5.9%` not `5.90%`.

**Experiment reports:** All experiment reports live on Empirium (team: sigma). Notion pages are archived references only. `docs/Experimentation-OS.md` defines the report structure and writing rules. The **Helix** agent (`.claude/agents/helix.md`) manages the full experiment lifecycle: draft, design, plan, run, analyze, present. Invoke with `claude --agent helix`.

**Where to find experiment details:** Each experiment with code has an experiment card (`.md` file in its directory) with hypothesis, decision rules, design decisions, and findings. Empirium is the source of truth for status, findings, and decisions. CLAUDE.md maps files, run commands, and Empirium IDs — not narratives.

**Hypothesis rules:** Every experiment hypothesis must be falsifiable — if no result can disprove it, rewrite until one can. On Empirium, the experiment **name** (title) IS the hypothesis (e.g., "Revisiting demoed merchants on day 2+ converts higher than single-visit"). Short noun-phrase titles go in the description header, not the name field. Hypotheses must be stated as a testable outcome claim, not as a goal or question.

**Empirium content rules:** Never reference named individuals (team leads, executives, external contacts) in Empirium experiment bodies, assumption evidence, or learnings. Use role/team language instead — "the ground force team was tasked with..." not "Brandon's memo directed...". Empirium is a shared institutional record; personal attributions don't belong there.

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

| ID | Directory | Pattern | What it tests | Empirium ID |
|----|-----------|---------|---------------|-------------|
| EXP-000 | `exp-000-merchant-network/` | B | Merchants as user-acquisition channel — CAC and retention analysis | — |
| EXP-001 | `exp-001-show-dont-tell/` | A | Demo-first opener vs verbal pitch | — |
| EXP-002 | `exp-002-social-proof-map/` | A | Showing nearby-merchant map at opener | — |
| EXP-004 | `exp-004-merchant-activation/` | B (queries only) | Tiered cash incentive to activate dormant merchants | — |
| EXP-005 | Notion-only | C | Growth Partner Incentive Model | — |
| EXP-006 | `exp-006-question-redirect/` | A | Universal redirect phrase for Q→Demo | — |
| EXP-007 | `exp-007-demo-dollars/` | A | Post-demo retargeting — do revisited merchants convert higher | EXP-005 |
| EXP-008 | `exp-008-gold-market-research/` | C | Merchant demand for digital gold | EXP-003 |
| EXP-009 | `exp-009-demo-shadow/` | C | Observational shadow of ambassador demos to identify execution gaps | — |
| EXP-010 | `exp-010-channel-yield/` | C | Which sourcing channels produce hires + flyer optimization | — |
| EXP-011 | Notion-only | C | Growth Partner Referrals | — |
| EXP-012 | `exp-012-student-interviews/` | C | University Students Outreach — structured interviews with student persona | EXP-016 |
| EXP-013 | `exp-013-question-deflection/` | C | Scripted deflection tool for Q→Demo redirect (physical field guide) | — |
| EXP-014 | `exp-014-ep-hook-vs-cta/` | A | EP CTA opener vs EP Hook — opener conversion rate and demo rate | — |
| — | `deprecated/exp-009-directed-day/` | B | Structured daily task lists with geo-clustered visits *(deprecated, was EXP-009)* | — |
| — | `deprecated/exp-018-direct-to-training/` | C | Direct-to-training hiring sprint *(deprecated)* | — |
| — | `deprecated/exp-020-ramadan-timing/` | A | Ramadan visit timing: daytime vs post-Taraweeh nighttime *(deprecated)* | — |

## Experiment Quick Reference

### EXP-000: Merchants Growing the ZAR Network

- **Status:** Complete
- **Files:** `exp-000-merchant-network/` (Pattern B standard files)
- **Queries:** `merchant_static_query()`, `user_onboardings_query()`, `user_activations_query()`, `merchant_daily_activity_query()`, `user_txn_breakdown_query()`, `user_invitations_query()`, `user_first_transactions_query()`, `user_cycling_query()`, `rapid_onboarding_query()`, `cycling_timing_query()`, `merchant_fraud_summary_query()`, `merchant_retention_query()`
- **Cache arrays:** `merchant_static`, `user_onboardings`, `user_activations`, `merchant_daily_activity`, `user_txn_breakdown`, `user_invitations`, `user_first_transactions`, `user_cycling`, `rapid_onboarding`, `cycling_timing`, `merchant_fraud_summary`, `merchant_retention`
- **Run:** `cd exp-000-merchant-network && python3 run.py --json <cache.json>`
- **Output:** `network_growth_through_merchants.html`
- **Empirium ID:** — (pending)
- **Notion page (archive):** `306003b8-300d-819a-bc08-f31aa413765e`
- **Finding:** Merchants onboarded 1,164 users (40 merchants), but 97.4% never return to transact. Merchants are a transaction channel, not an acquisition channel. CAC $0.82.

### EXP-001: Show Don't Tell

- **Files:** `exp-001-show-dont-tell/` (Pattern A standard files)
- **Empirium ID:** — (pending)
- **Notion page (archive):** `304003b8-300d-8130-86db-d02471345411`
- **Run:** `cd exp-001-show-dont-tell && python3 run.py`
- **Output:** `dont_show_tell_exp.html`

### EXP-002: Social Proof Map

- **Files:** `exp-002-social-proof-map/` (Pattern A standard files)
- **Experiment card:** `exp-002-social-proof-map/exp-002-social-proof-map.md`
- **Empirium ID:** — (pending)
- **Notion page (archive):** `304003b8-300d-8132-bc22-fdb87bbf7864`
- **Run:** `cd exp-002-social-proof-map && python3 run.py`
- **Output:** `social_proof_map.html`

### EXP-004: Merchant Activation Incentive

- **Files:** `exp-004-merchant-activation/queries.py`, `exp-004-merchant-activation/growth-partner-incentive-structure.md`
- **Queries:** `merchant_qualification_query()`, `distribution_summary_query()`, `fraud_signals_query()`
- **Empirium ID:** — (pending)
- **Notion page (archive):** `304003b8-300d-81f7-8957-cb0636073abd`
- **Data refresh:** Run queries via Rube MCP → results go directly to Notion (no cache JSON or HTML dashboard)

### EXP-006: Question Redirect Protocol

- **Files:** `exp-006-question-redirect/` (Pattern A + DB overlay via `queries.py`)
- **Experiment card:** `exp-006-question-redirect/exp-006-question-redirect.md`
- **Queries:** `demo_onboarding_status_query()`
- **Cache arrays:** `db_status`
- **Empirium ID:** — (pending)
- **Notion page (archive):** `306003b8-300d-8195-b35c-e9d072bd8d24`
- **Run:** `cd exp-006-question-redirect && python3 run.py` (sheet-only) or `python3 run.py --json db_status.json` (DB-verified)
- **Output:** `question_redirect.html`

### EXP-007: Post-Demo Retargeting

- **Files:** `exp-007-demo-dollars/` (Pattern A standard files)
- **Experiment card:** `exp-007-demo-dollars/exp-007-post-demo-retargeting.md`
- **Empirium ID:** EXP-005
- **Notion page (archive):** `306003b8-300d-8118-a728-f93f4f321d6e`
- **Run:** `cd exp-007-demo-dollars && python3 run.py`
- **Output:** `post_demo_retargeting.html`
- **Analysis:** Retrospective — groups onboarding visits by merchant phone, compares conversion of retargeted (2+ visit days) vs not-retargeted merchants from the "retarget pool" (demoed but not onboarded on first visit)

### EXP-008: Digital Gold Market Research

- **Experiment card:** `exp-008-gold-market-research/exp-008-digital-gold.md`
- **Empirium ID:** EXP-003
- **Notion page (archive):** `306003b8-300d-817c-9221-d858c9638c36`

### Directed Day *(deprecated, was EXP-009)*

- **Files:** `deprecated/exp-009-directed-day/` — `run.py`, `queries.py`, `task_generator.py`, `ui/` (Pattern B)
- **Experiment card:** `deprecated/exp-009-directed-day/exp-009-directed-day.md`
- **Queries:** `reactivation_targets_query()`, `onboarding_status_check_query()`, `onboarding_outcome_query()`, `reactivation_outcome_query()`, `pool_health_query()`
- **Run:** `cd deprecated/exp-009-directed-day && python3 run.py --json targets_cache.json` (dashboard) or add `--generate` (generate routes + dashboard)

### EXP-009: Demo Shadow

- **Files:** `exp-009-demo-shadow/shadow-experiment-v2.pdf`
- **Empirium ID:** — (pending)
- **Notion page (archive):** `309003b8-300d-8100-8420-ec6c6be3737c`
- **Status:** Draft (planned)
- **Design:** Observational shadow of 4 ambassadors × 3 visits (12 sessions) to identify execution gaps behind 20–25% demo rate. Non-intervention, directional findings only.

### EXP-010: Channel Yield + Flyer Optimization

- **Files:** `exp-010-channel-yield/` (Pattern C)
- **Experiment card:** `exp-010-channel-yield/exp-010-channel-yield.md`
- **Tracking sheet:** `1Y3o_BfXk3rdREHEpLc3SBdwWFJd4DfKmuf0hwh-BZYI` — tabs: "Feb 18 Onwards" (pipeline), "Broadcast Log" (flyer tracking)
- **Empirium ID:** — (pending)
- **Note:** Originally EXP-019. Ran in parallel with EXP-018 (now deprecated).

### EXP-013: Question Deflection Tool

- **Files:** `exp-013-question-deflection/` (Pattern C)
- **Experiment card:** `exp-013-question-deflection/exp-013-question-deflection.md`
- **Artifact:** `exp-013-question-deflection/deflection-guide.html` (mobile-first field tool, 8 deflection categories)
- **Empirium ID:** — (pending)
- **Parent:** EXP-006 (Question Redirect)
- **Status:** DESIGN

### EXP-018: Direct-to-Training *(deprecated)*

- **Files:** `deprecated/exp-018-direct-to-training/` — experiment card + flyers
- **Artifacts:** `deprecated/exp-018-direct-to-training/flyers/growth-partner-flyer.html`, Urdu variant, `sheet-guide.html`
- **PNG renders:** `deprecated/exp-018-direct-to-training/flyers/growth-partner-flyer.png`, `deprecated/exp-018-direct-to-training/flyers/growth-partner-flyer-ur.png`

### EXP-020: Ramadan Visit Timing *(deprecated)*

- **Files:** `deprecated/exp-020-ramadan-timing/` (Pattern A standard files + time bucketing extensions)
- **Experiment card:** `deprecated/exp-020-ramadan-timing/exp-020-ramadan-timing.md`
- **Run:** `cd deprecated/exp-020-ramadan-timing && python3 run.py`

### EXP-012: University Students Outreach

- **Files:** `exp-012-student-interviews/` (Pattern C + transcription script)
- **Experiment card:** `exp-012-student-interviews/exp-012-student-interviews.md`
- **Status:** RUNNING — 60/30 interviews collected, mid-flight quality check done
- **Hypothesis:** Structured interviews with university students identify motivations, concerns, and language that differentiate the student persona from order bookers
- **Data:**
  - `survey_responses.csv` — 60 form responses (32 columns)
  - `analysis.md` — thematic analysis (sample, interest, pay, personas, quotes)
  - `Voice recording of surveys/` — 13 .m4a voice recordings + .txt transcripts
  - `transcripts.md` — combined transcripts (Whisper medium, `language="en"` for Roman Urdu + English)
  - `transcribe.py` — batch Whisper transcription script
- **HTML artifact:** `student_outreach_check.html` — mid-flight quality check card with Eric (experiment quality) + Nash (incentive design) analysis
- **Key findings (preliminary):** 90% Medium+ interest, 3 sub-personas (Hustler 15-20%, Cautious Pragmatist 50-55%, Reluctant Observer 10-15%), optimal pay = base PKR 15-20K + per-merchant bonuses
- **Critical flags:** 48% single-interviewer concentration (Ahmed Abdul Rauf, zero recordings), 82% friend/referral sampling bias, form-vs-recording data gaps, zero probing in all recordings
- **Google Form:** `1FAIpQLSewfIKLAZ12cmxt5hrt-FbK3wnOuoR7p75W4yr2feJ6poqXxg`
- **Google Sheet:** `1V8QbgRjG_GdW_C7Ko71NtGHrmQr0ATKTuExBvgcwb1E`
- **Notion page (archive):** `312003b8300d81e48beed012da974177`
- **Empirium ID:** EXP-016

### EXP-014: EP Hook vs CTA Opener A/B

- **Files:** `exp-014-ep-hook-vs-cta/` (Pattern A standard files)
- **Empirium ID:** — (pending)
- **Status:** RUNNING — 53 CTA visits logged (target: 100)
- **Hypothesis:** EP CTA opener outperforms EP hook on both opener conversion rate and demo rate
- **Google Sheet:** `1bFf0NAQFFXIYYxMC1yJeqowRz6MwT_-xawZeg5H9wUQ` (tab: Form Responses 1; Tagging tab = ambassador name map)
- **Run:** `cd exp-014-ep-hook-vs-cta && python3 run.py --from 2026-03-02`
- **Output:** `opener_comparison.html`
- **Decision criteria:** ADOPT if CTA opener rate ≥ Hook AND CTA demo rate ≥ Hook on both metrics

### Notion-Only Experiments

- EXP-005: Growth Partner Incentive Model
- EXP-011: Growth Partner Referrals

## Shared SQL Library — `lib/sql.py`

All experiments import shared constants and CTE generators from `lib/sql.py` (package: `lib/__init__.py`). Single source of truth for exclusion lists, merchant/ambassador definitions, and onboarding checks.

**Import pattern** (in each experiment's `queries.py`):
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from lib.sql import EXCLUDED_IDS_SQL, merchants_cte, ambassadors_cte
```

**Constants:**

| Name | Count | Purpose |
|------|-------|---------|
| `EXCLUDED_IDS` / `EXCLUDED_IDS_SQL` | 19 IDs | Test/internal UUIDs excluded from all queries |
| `COHORT_TXN_EXCLUDED_IDS` / `COHORT_TXN_EXCLUDED_IDS_SQL` | 12 IDs | Subset for transaction cohort analysis |

**CTE generators:**

| Function | Signature | Returns CTE(s) | Used by |
|----------|-----------|----------------|---------|
| `ambassadors_cte` | `()` | `ambassadors` | exp-007-demo-dollars, exp-006-question-redirect |
| `merchants_cte` | `(city=None, since=None)` | `mos_merchants`, `pe_merchants`, `merchants`; + `qualifying` if `since` set | exp-000-merchant-network, deprecated/exp-009-directed-day, exp-004-merchant-activation |
| `merchant_sales_cte` | `()` | `merchant_sales` (ZCE orders + CashExchange) | exp-004-merchant-activation, deprecated/exp-009-directed-day, exp-000-merchant-network |
| `demo_dollars_cte` | `()` | `demo_dollars` (requires `ambassadors` CTE in scope) | exp-007-demo-dollars |
| `is_onboarded_check` | `(user_id_col, phone_col)` | Boolean expression (not a CTE) | exp-007-demo-dollars |

**`merchants_cte()` notes:**
- `city="Karachi"` → filters MOS by city. PE has no city field (returns 0 PE rows with city filter — known limitation).
- `since="2026-02-01"` → adds `qualifying` CTE. Downstream queries should reference `qualifying` instead of `merchants`.

**Rule:** When the DB schema changes (new onboarding pathway, new exclusion list entry), fix `lib/sql.py` once. All experiments inherit the fix automatically.

### Central Query Registry — `lib/queries.py`

Every SQL query function in the repo is importable from `lib/queries.py`. Use this as the single entry point for Rube MCP and Helix when you need a query by name without knowing which experiment it lives in.

```python
from lib.queries import recipient_overview_query, pool_health_query  # etc.
```

Covers: EXP-000, EXP-004, EXP-006, EXP-007, deprecated Directed Day.

## DB Schema

### Ambassador ID → Name Mappings

| User ID | Username | Real Name |
|---------|----------|-----------|
| `019bfeae-4ab6-77ef-8fe5-7fb91c7755ce` | `user_1ef1d1ea` | Arslan Ansari |
| `019c22a1-07a6-7c67-889e-5c655fe8ae11` | `owaisferoz1` | Owais Feroz |
| `a9519a82-c510-4b5b-a24b-ecec3f68de23` | `muhammadzahid` | Muhammad Zahid |

### Schema Facts

- No `shops` table — use `merchant_onboarding_submissions` for business info
- `merchant_onboarding_submissions`: `business_name`, `phone_number`, `status`, `onboarder_id`, `city`, `latitude`, `longitude`
- `users`: `phone_number`, `username`, `first_name`, `last_name`, `email`
- "Secured account" = `(email is not null and email != '') or (phone_number is not null and phone_number != '')`
- PostgreSQL does NOT support `min()` on UUID — must cast: `min(col::text)::uuid`
- No session/event/analytics tables in DB — app open data lives only in Amplitude
- Transaction types: `Transaction::CardSpend`, `Transaction::BankTransfer` (status = 3 for completed)
- ZCE orders: `zar_cash_exchange_orders` — `initiator_id` = user, `fulfiller_id` = merchant, `status = 'completed'`
- Cash notes: `digital_cash_notes` — `depositor_id` = sender, `claimant_id` = receiver, `status = 'claimed'`
- PKT time offset: `+ interval '5' hour` for UTC → Pakistan Time
- `product_enrollments`: `user_id`, `state` (0=available, 1=onboarding, 2=enabled, 3=disabled), `product_definition_id`, `created_at`
- `product_definitions`: `code` column, merchant code = `'zar_cash_exchange_merchant'`
- Since Dec 13 (SHIP-2069), new merchants use `product_enrollments` instead of `merchant_onboarding_submissions`. All merchant queries UNION both sources (MOS + PE). Zero overlap.
- `Transaction::CashExchange` — new transaction type for merchant cash note sales. Lives on `transactions` table. Each sale creates two rows: merchant-side (`direction=0`, `metadata->>'role' = 'merchant'`) and customer-side (`direction=1`, `metadata->>'role' = 'customer'`). Metadata contains `ad_snapshot` (rate, currency, merchant_name), `cash_note_ref`, `counterparty_id`. `status = 3` = completed, `amount` = atomic USDC (÷ 1e6 for dollars). Filter `coalesce(metadata->>'cancelled', 'false') != 'true'` to exclude cancelled.
- Since ~Feb 2026, nearly all merchant activity uses `Transaction::CashExchange` (via `digital_cash_notes`) instead of `zar_cash_exchange_orders`. ZCE orders have flatlined. All merchant queries UNION both ZCE + CashExchange sources via `merchant_sales_cte()` in `lib/sql.py`.

## Rube MCP (Composio)

### Metabase (SQL Queries)
- Tool: `METABASE_POST_API_DATASET` with `database: 1`, `type: "native"`, `native: {query: "..."}`
- Works via both `RUBE_MULTI_EXECUTE_TOOL` and workbench
- Session ID: `"each"`

### Amplitude (App Analytics)
- Tools: `AMPLITUDE_FIND_USER` (UUID → amplitude_id), `AMPLITUDE_GET_USER_ACTIVITY` (event stream)
- **Critical**: These tools FAIL via `RUBE_MULTI_EXECUTE_TOOL` (routes to `api2.amplitude.com`, returns 404)
- **Workaround**: Use `run_composio_tool()` inside `RUBE_REMOTE_WORKBENCH`
- **Primary event type**: `"[Amplitude] Application Opened"` (this is the dominant one — most app open events use this exact string)
- All event type keywords to match: `"Application Opened"`, `"Start Session"`, `"app_open"`, `"App Open"`, `"app_opened"`, `"session_start"`
- `AMPLITUDE_FIND_USER` parameter is `{"user": "<uuid>"}` (NOT `user_search_id`)

### Cache JSON Workflow

1. Write/update SQL in `queries.py` (canonical source of truth)
2. Run query via `METABASE_POST_API_DATASET` → extract `rows` from `data.data.rows`
3. Map column names from `data.data.cols[].name` to build JSON objects
4. For Amplitude data: batch via `RUBE_REMOTE_WORKBENCH` using `run_composio_tool()`
5. Update local `*_cache.json` file with new/updated arrays
6. Run `python3 run.py --json *_cache.json` to regenerate HTML

## Notion MCP

> Notion is an archived reference. Use Empirium MCP for all active experiment tracking.

**Tools**: `notion-fetch`, `notion-update-page`, `notion-search`, `notion-create-pages`

**Server name**: `claude.ai Notion` (with dots and spaces — NOT `claude_ai_Notion`)

**Experiment Tracker collection**: `304003b8-300d-8105-b1a5-000bb19137b1`

**Page IDs:**

| Experiment | Page ID |
|-----------|---------|
| EXP-000 | `306003b8-300d-819a-bc08-f31aa413765e` |
| EXP-001 | `304003b8-300d-8130-86db-d02471345411` |
| EXP-002 | `304003b8-300d-8132-bc22-fdb87bbf7864` |
| EXP-004 | `304003b8-300d-81f7-8957-cb0636073abd` |
| EXP-006 | `306003b8-300d-8195-b35c-e9d072bd8d24` |
| EXP-007 | `306003b8-300d-8118-a728-f93f4f321d6e` |
| EXP-008 | `306003b8-300d-817c-9221-d858c9638c36` |
| EXP-009 | `309003b8-300d-8100-8420-ec6c6be3737c` |

**Content update commands** (in order of reliability):
1. **`replace_content`** — replaces entire page. Most reliable.
2. **`insert_content_after`** — appends after matched text. Ensure selection is unique.
3. **`replace_content_range`** — **unreliable inside callout blocks** (fails with "String not found"). Workaround: use `replace_content` with full page.

**Dollar sign escaping**: Use `\\$` in Notion markdown (e.g., `\\$10` renders as `$10`).

**Notion-flavored markdown reference**: `ReadMcpResourceTool` with server `claude.ai Notion`, URI `notion://docs/enhanced-markdown-spec`.

**Formatting patterns:**
- Callout: `<callout icon="📋" color="blue_bg">` with tab-indented content
- Colored table rows: `<tr color="green_bg">`, `yellow_bg`, `red_bg`, `blue_bg`
- Toggle headings: `## Heading {toggle="true"}` with tab-indented children (no color attribute — headings render in black)
- Tables: `<table header-row="true">` with `<colgroup>/<col width="N">` for column widths

## Notion Editing Rules

- When editing Notion pages, act directly on the page — do not write to a local file first.
- Use HTML tables (not pipe-tables) with `<td>` on separate tab-indented lines per Notion spec.
- Never use emoji circles or decorative formatting — keep it professional and clean.
- Keep content concise: use final numbers and verdicts, not verbose templates.
- Always verify after editing: re-read the page to confirm no missed items (e.g., leftover stale mentions, wrong status values).

## Verbosity

Be concise. Prefer final data, clean numbers, and verdicts — not detailed templates, exhaustive explanations, or lengthy writeups. When updating docs or reports, default to tight, executive-style prose unless told otherwise.

## Tools & Integrations

### Empirium (Experiment Tracking)

**Team slug:** `sigma`
**Tools:** `experiments_list`, `experiments_get`, `experiments_create`, `experiments_update`, `experiments_transition`, `experiments_decide`, `experiments_add_learning`
**Source of truth for:** status, hypothesis, success criteria, MVT, results, decisions, learnings

**Warning — side effect on `experiments_update`:** Calling `experiments_update` with only `description` can silently overwrite the `hypothesis` field (Empirium appears to auto-generate it from the description). Always verify the `hypothesis` value after any update call, and restore it immediately if it changed.

**No named individuals in Empirium content:** Never mention specific people's names (team leads, executives, stakeholders) in experiment descriptions, assumption evidence, or learnings. Use role/team language ("the ground force team", "the product team") — Empirium is an institutional record, not a meeting log.

### MCP Integrations

Available MCP servers include Google Drive (via Rube), Notion, Slack, Linear, Figma, and others. Check available MCP tools before saying you can't access a service. Use `ToolSearch` if unsure what's available.

## Glossary

**Nash**, **Terra**, **Atlas**, and **Eric** are agents in the Canon repository (`/Users/asharib/Documents/GitHub/canon/`):
- **Eric** — Empirium Architect. Structures Initiatives, Assumptions, and Experiments with falsifiable hypotheses, success criteria, and decision rules. First point of contact for Empirium work.
- **Nash** — Game theory expert. Designs incentive systems where fraud is economically irrational using mechanism design, auction theory, and Nash equilibria. Stress-tests systems for exploits.
- **Terra** — Field sales expert and Ground Force coach. Stress-tests ambassador training materials and pitch flows by simulating real merchant/ambassador personas before they ship.
- **Atlas** — Data navigator. Writes SQL queries and retrieves insights from the ZAR database. Uses a Five Questions Framework (metric, entity scope, time, grouping, output format) before writing any query.
