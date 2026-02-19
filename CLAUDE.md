# Ground Force Experiments

Standalone experiment tracking for Zar's ground force (field ambassador) team. Each subdirectory is one experiment.

## Conventions

**Session hygiene:** After approximately 30 turns in a conversation, remind the user to start a fresh session or use `/compact` to reduce context size and save tokens. Say something like: "We're at ~30 turns — consider starting a fresh session or running /compact to keep token usage lean."

**Model usage:** Use Sonnet for routine tasks (simple searches, straightforward edits, boilerplate generation). Reserve Opus for complex reasoning, architectural decisions, and multi-step problem solving.

**Output rules:** Always show the full pipe table and insights output to the user (do not suppress or summarize). This applies to all Pattern A experiments.

**Percentage formatting:** All percentages use 2 significant digits via `_sig2()` helper. Terminal `output.py` and HTML `flowchart.py` must both use this function. Example: `18%` not `18.0%`, `5.9%` not `5.90%`.

**Experiment reports:** All experiment reports live on Notion (Experiment Tracker database). `Experimentation-OS.md` defines the report structure and writing rules. The **Helix** agent (`.claude/agents/helix.md`) manages the full experiment lifecycle: draft, design, plan, run, analyze, present. Invoke with `claude --agent helix`.

Key principles: lead with verdict (SHIP IT / ITERATE / KILL IT / NEEDS MORE DATA), include statistical validity check, use INSIGHT/Evidence/Implication format, prefer observed metrics over self-reported.

**Where to find experiment details:** Each experiment with code has an experiment card (`.md` file in its directory) with hypothesis, decision rules, design decisions, and findings. Notion pages have the latest reports. CLAUDE.md only maps files, run commands, and IDs — not narratives.

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

| ID | Directory | Pattern | What it tests |
|----|-----------|---------|---------------|
| EXP-001 | `show-dont-tell/` | A | Demo-first opener vs verbal pitch |
| EXP-002 | `social-proof-map/` | A | Showing nearby-merchant map at opener |
| EXP-004 | `exp-004-merchant-activation/` | B (queries only) | Tiered cash incentive to activate dormant merchants |
| EXP-006 | `question-redirect/` | A | Universal redirect phrase for Q→Demo |
| EXP-008 | `gold-market-research/` | C | Merchant demand for digital gold |
| EXP-009 | `directed-day/` | B | Structured daily task lists with geo-clustered visits |
| EXP-018 | `exp-018-direct-to-training.md` + `hiring-flyer/` | C | Direct-to-training hiring sprint |
| EXP-019 | `exp-019-channel-yield.md` | C | Which sourcing channels produce hires |
| — | `merchant-user-onboardings/` | B | Merchant onboarding, activation, retention dashboard |
| — | `demo-dollars-usage/` | B | What demo-dollar recipients did (includes EXP-007) |
| EXP-010–017 | Notion-only | C | See Notion-only experiments below |

## Experiment Quick Reference

### EXP-001: Show Don't Tell

- **Files:** `show-dont-tell/` (Pattern A standard files)
- **Notion page:** `304003b8-300d-8130-86db-d02471345411`
- **Run:** `cd show-dont-tell && python3 run.py`
- **Output:** `dont_show_tell_exp.html`

### EXP-002: Social Proof Map

- **Files:** `social-proof-map/` (Pattern A standard files)
- **Experiment card:** `social-proof-map/exp-002-social-proof-map.md`
- **Notion page:** `304003b8-300d-8132-bc22-fdb87bbf7864`
- **Run:** `cd social-proof-map && python3 run.py`
- **Output:** `social_proof_map.html`

### EXP-004: Merchant Activation Incentive

- **Files:** `exp-004-merchant-activation/queries.py`, `growth-partner-incentive-structure.md`
- **Queries:** `merchant_qualification_query()`, `distribution_summary_query()`, `fraud_signals_query()`
- **Notion page:** `304003b8-300d-81f7-8957-cb0636073abd`
- **Data refresh:** Run queries via Rube MCP → results go directly to Notion (no cache JSON or HTML dashboard)

### EXP-006: Question Redirect Protocol

- **Files:** `question-redirect/` (Pattern A + DB overlay via `queries.py`)
- **Experiment card:** `question-redirect/exp-006-question-redirect.md`
- **Queries:** `demo_onboarding_status_query()`
- **Cache arrays:** `db_status`
- **Notion page:** `306003b8-300d-8195-b35c-e9d072bd8d24`
- **Run:** `cd question-redirect && python3 run.py` (sheet-only) or `python3 run.py --json db_status.json` (DB-verified)
- **Output:** `question_redirect.html`

### EXP-008: Digital Gold Market Research

- **Experiment card:** `gold-market-research/exp-008-digital-gold.md`
- **Notion page:** `306003b8-300d-817c-9221-d858c9638c36`

### EXP-009: Directed Day

- **Files:** `directed-day/` — `run.py`, `queries.py`, `task_generator.py`, `ui/` (Pattern B)
- **Experiment card:** `directed-day/exp-009-directed-day.md`
- **Queries:** `reactivation_targets_query()`, `onboarding_status_check_query()`, `onboarding_outcome_query()`, `reactivation_outcome_query()`, `pool_health_query()`
- **Run:** `cd directed-day && python3 run.py --json targets_cache.json` (dashboard) or add `--generate` (generate routes + dashboard)

### Merchant-User Onboardings (dashboard)

- **Files:** `merchant-user-onboardings/` (Pattern B standard files)
- **Run:** `cd merchant-user-onboardings && python3 run.py --json <cache.json>`

### Demo Dollars Usage (EXP-001+ / EXP-007)

- **Files:** `demo-dollars-usage/` (Pattern B standard files)
- **Queries:** `recipient_overview_query()`, `note_distribution_query()`, `recipient_activity_query()`, `ambassador_summary_query()`, `recipient_timing_query()`, `demo_merchant_transactions_query()`, `time_to_first_tx_query()`, `all_activity_timestamps_query()`
- **Cache arrays:** `recipient_overview`, `note_distribution`, `recipient_activity`, `ambassador_summary`, `app_opens`, `recipient_timing`, `app_opens_detailed`, `merchant_transactions`, `time_to_first_tx`
- **Run:** `cd demo-dollars-usage && python3 run.py --json <cache.json>`
- **Notion page:** `306003b8-300d-8118-a728-f93f4f321d6e`
- **Note:** `app_opens` and `app_opens_detailed` sourced from Amplitude (not SQL) — see Rube MCP section

### EXP-018 + EXP-019: Hiring Sprint

EXP-018 (pipeline) and EXP-019 (channel yield) share a single tracking sheet and run as one sprint.

- **Experiment cards:** `exp-018-direct-to-training.md`, `exp-019-channel-yield.md`
- **Artifacts:** `hiring-flyer/growth-partner-flyer.html`, `hiring-flyer/growth-partner-flyer-ur.html` (Urdu variant), `hiring-flyer/sheet-guide.html`
- **PNG renders:** `hiring-flyer/growth-partner-flyer.png`, `hiring-flyer/growth-partner-flyer-ur.png`
- **Tracking sheet:** `1Y3o_BfXk3rdREHEpLc3SBdwWFJd4DfKmuf0hwh-BZYI` — tabs: "Feb 18 Onwards" (pipeline), "Broadcast Log" (flyer tracking)
- **Notion pages:** EXP-018 `30a003b8-300d-816a-9f2d-da9328a7f891`, EXP-019 `30a003b8-300d-8183-b8f1-e65d3d1b2e6f`

### Notion-Only Experiments (EXP-010 — EXP-017)

**Pakistan Pitch & Training:**
- EXP-010: Demo Shadow — explain Q-to-Demo variance across ambassadors
- EXP-011: WhatsApp Follow-Up — 2h post-demo WhatsApp template
- EXP-012: Preemptive Pitch — 15s "how it works" explanation before demo

**Bangladesh Market Entry:**
- EXP-013: Market Structure Mapping — 30 interviews across 3 Dhaka zones
- EXP-014: Tracking Infrastructure — forms, GPS, timezone for BD
- EXP-015: Pitch A/B — savings vs remittance framing
- EXP-016: Cross-Market Benchmark — PK vs BD funnel comparison

**Hiring & Recruitment:**
- EXP-017: Top Performer DNA — pre-hire trait profiling (r > 0.5 threshold)

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
| `ambassadors_cte` | `()` | `ambassadors` | demo-dollars-usage, question-redirect |
| `merchants_cte` | `(city=None, since=None)` | `mos_merchants`, `pe_merchants`, `merchants`; + `qualifying` if `since` set | merchant-user-onboardings, directed-day, exp-004 |
| `demo_dollars_cte` | `()` | `demo_dollars` (requires `ambassadors` CTE in scope) | demo-dollars-usage |
| `is_onboarded_check` | `(user_id_col, phone_col)` | Boolean expression (not a CTE) | demo-dollars-usage |

**`merchants_cte()` notes:**
- `city="Karachi"` → filters MOS by city. PE has no city field (returns 0 PE rows with city filter — known limitation).
- `since="2026-02-01"` → adds `qualifying` CTE. Downstream queries should reference `qualifying` instead of `merchants`.

**Rule:** When the DB schema changes (new onboarding pathway, new exclusion list entry), fix `lib/sql.py` once. All experiments inherit the fix automatically.

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

## Rube MCP (Composio)

### Metabase (SQL Queries)
- Tool: `METABASE_POST_API_DATASET` with `database: 1`, `type: "native"`, `native: {query: "..."}`
- Works via both `RUBE_MULTI_EXECUTE_TOOL` and workbench
- Session ID: `"each"`

### Amplitude (App Analytics)
- Tools: `AMPLITUDE_FIND_USER` (UUID → amplitude_id), `AMPLITUDE_GET_USER_ACTIVITY` (event stream)
- **Critical**: These tools FAIL via `RUBE_MULTI_EXECUTE_TOOL` (routes to `api2.amplitude.com`, returns 404)
- **Workaround**: Use `run_composio_tool()` inside `RUBE_REMOTE_WORKBENCH`
- Event types for app opens: `"app_open"`, `"session_start"`, `"[Amplitude] Start Session"`, `"App Open"`, `"app_opened"`

### Cache JSON Workflow

1. Write/update SQL in `queries.py` (canonical source of truth)
2. Run query via `METABASE_POST_API_DATASET` → extract `rows` from `data.data.rows`
3. Map column names from `data.data.cols[].name` to build JSON objects
4. For Amplitude data: batch via `RUBE_REMOTE_WORKBENCH` using `run_composio_tool()`
5. Update local `*_cache.json` file with new/updated arrays
6. Run `python3 run.py --json *_cache.json` to regenerate HTML

## Notion MCP

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
| EXP-010 | `309003b8-300d-8100-8420-ec6c6be3737c` |
| EXP-011 | `309003b8-300d-815c-9f49-d830d0be7ff5` |
| EXP-012 | `309003b8-300d-8180-b1b6-f23367b57a52` |
| EXP-013 | `309003b8-300d-8194-9a9c-f377f3426b51` |
| EXP-014 | `309003b8-300d-8188-9e86-c0f999021fa0` |
| EXP-015 | `309003b8-300d-81f8-a7eb-ca9409b163d4` |
| EXP-016 | `309003b8-300d-81e4-8105-fcc7e9f7688d` |
| EXP-017 | `309003b8-300d-8117-ad4d-c5323ab320b1` |
| EXP-018 | `30a003b8-300d-816a-9f2d-da9328a7f891` |
| EXP-019 | `30a003b8-300d-8183-b8f1-e65d3d1b2e6f` |

**Missing from Notion**: EXP-009 (Directed Day) — no Notion page found.

**Content update commands** (in order of reliability):
1. **`replace_content`** — replaces entire page. Most reliable.
2. **`insert_content_after`** — appends after matched text. Ensure selection is unique.
3. **`replace_content_range`** — **unreliable inside callout blocks** (fails with "String not found"). Workaround: use `replace_content` with full page.

**Dollar sign escaping**: Use `\\$` in Notion markdown (e.g., `\\$10` renders as `$10`).

**Notion-flavored markdown reference**: `ReadMcpResourceTool` with server `claude.ai Notion`, URI `notion://docs/enhanced-markdown-spec`.

**Formatting patterns:**
- Callout: `<callout icon="📋" color="blue_bg">` with tab-indented content
- Colored table rows: `<tr color="green_bg">`, `yellow_bg`, `red_bg`, `blue_bg`
- Toggle headings: `▶## Heading {color="gray"}` with tab-indented children
- Tables: `<table header-row="true">` with `<colgroup>/<col width="N">` for column widths

## Glossary

**Nash**, **Terra**, and **Atlas** are agents in the Canon repository (`/Users/asharib/Documents/GitHub/canon/`):
- **Nash** — Game theory expert. Designs incentive systems where fraud is economically irrational using mechanism design, auction theory, and Nash equilibria. Stress-tests systems for exploits.
- **Terra** — Field sales expert and Ground Force coach. Stress-tests ambassador training materials and pitch flows by simulating real merchant/ambassador personas before they ship.
- **Atlas** — Data navigator. Writes SQL queries and retrieves insights from the ZAR database. Uses a Five Questions Framework (metric, entity scope, time, grouping, output format) before writing any query.
