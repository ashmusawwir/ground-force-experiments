# Ground Force Experiments

Standalone experiment tracking for Zar's ground force (field ambassador) team. Each subdirectory is one experiment.

## Session Hygiene

After approximately 30 turns in a conversation, remind the user to start a fresh session or use `/compact` to reduce context size and save tokens. Say something like: "We're at ~30 turns — consider starting a fresh session or running /compact to keep token usage lean."

## Model Usage

Use Sonnet for routine tasks (simple searches, straightforward edits, boilerplate generation). Reserve Opus for complex reasoning, architectural decisions, and multi-step problem solving.

## Show Don't Tell Experiment

Tests a new opener strategy where ambassadors demonstrate the app instead of pitching verbally. Started Feb 10, 2026.

### Run
```bash
cd /Users/asharib/Documents/GitHub/ground-force-experiments/show-dont-tell
python3 run.py
```

Outputs: baseline vs experiment funnel comparison, per-ambassador breakdown, and updates the flowchart HTML.

**Note:** Always show the full pipe table and insights output to the user (do not suppress or summarize).

### Files

| File | Purpose |
|------|---------|
| `run.py` | Single entry point (~30 lines) |
| `config.py` | Experiment constants: name, dates, sheet ID, 7 column names |
| `data.py` | Fetch sheet + parse timestamps + row classifiers |
| `funnel.py` | Pure computation: FunnelMetrics, FlowchartNodes, ambassador breakdown |
| `output.py` | All terminal printing: tables + insights |
| `flowchart.py` | Generate HTML flowchart from scratch (CSS/SVG constants + dynamic nodes) |
| `dont_show_tell_exp.html` | Generated artifact (overwritten each run) |

### Architecture

Clean DAG — no circular deps:
```
config  ←  data  ←  funnel  ←  output
                       ↑
                   flowchart
                       ↑
                     run.py
```

## Network Growth Through Merchants

Tracks merchant-user onboardings, activation, transacting users, and merchant retention. Self-contained HTML one-pager with interactive date picker, city filter, sortable tables, and Chart.js retention chart.

### Run
```bash
cd /Users/asharib/Documents/GitHub/ground-force-experiments/merchant-user-onboardings
python3 run.py --json <path-to-cache.json>
```

Outputs: `network_growth_through_merchants.html` — self-contained HTML with 4 sections.

### Architecture

Assembly pattern: `shell.html` + `style.css` + `app.js` → single HTML via string injection.

| File | Purpose |
|------|---------|
| `run.py` | Entry point: reads cache JSON, assembles HTML (~55 lines) |
| `queries.py` | SQL queries (merchant_summary + merchant_retention) with tier-split earnings CTEs |
| `ui/shell.html` | HTML skeleton with injection markers |
| `ui/style.css` | All CSS |
| `ui/app.js` | JS rendering, filters, calendar, earnings computation |
| `network_growth_through_merchants.html` | Generated artifact (overwritten each run) |

### Earnings Model

Two incentive tiers based on onboarding date:
- **Tier 1** (Jan 1 – Jan 27, 2026): $1.00 per user onboarded
- **Tier 2** (Jan 28, 2026+): $0.50 per user onboarded + $0.50 per activated user

`earnings = (tier1_onboarded × $1.00) + (tier2_onboarded × $0.50) + (tier2_activated × $0.50)`

### Data Source

Reads `merchant_summary` and `merchant_retention` arrays from a cache JSON file. The `queries.py` file contains the canonical SQL for fetching this data via Rube MCP (Metabase database ID 1).

## Demo Dollars Usage Analysis

Traces what non-onboarded recipients did with the $5 demo cash notes ambassadors gave them. Identifies who "understood the product" enough to be worth revisiting. Self-contained HTML one-pager with story cards.

### Run
```bash
cd /Users/asharib/Documents/GitHub/ground-force-experiments/demo-dollars-usage
python3 run.py --json <path-to-cache.json>
```

Outputs: `demo_dollars_usage.html` — self-contained HTML with 8 story cards.

### Architecture

Assembly pattern: `shell.html` + `style.css` + `app.js` → single HTML via string injection.

| File | Purpose |
|------|---------|
| `run.py` | Entry point: reads cache JSON, assembles HTML |
| `queries.py` | SQL queries (5 queries + shared CTEs) following Atlas conventions |
| `ui/shell.html` | HTML skeleton with injection markers |
| `ui/style.css` | Zar theme CSS (includes `.recommendation-box`, `.insight-box`, `.amount-table`) |
| `ui/app.js` | Client-side rendering, scoring, story cards, timing analysis |
| `demo_dollars_usage.html` | Generated artifact (overwritten each run) |

### Iterations

| Iter | What was added |
|------|----------------|
| 1 | Story cards, non-onboarded scoping, recipient detail table |
| 2 | Better identifiers (names, phone), secured account check |
| 3 | Cycling redefinition (full round-trip only), ambassador breakdown |
| 4 | Timing analysis ("When Do They Act?"), amount effectiveness ("Is $5 the Right Amount?"), "Days to Act" detail column, Amplitude app opens data |
| 5 | Brand recall analysis (timestamped app opens, 2h+ = brand recall), hours precision (timing card), executive summary, self-serving report (inline definitions, Terra communication principles) |
| 6 | Visit sheet enrichment (shop names + geocoordinates from Google Sheet), Location column in Revisit Targets with Google Maps links, CSV download button |

### "Understands the Product" Definition

Binary classification: demonstrated active use of at least one core product capability beyond passive receipt, excluding cycling back to the ambassador.

**Qualifying actions** (any one = understood): sent cash note to non-ambassador, card purchase, bank transfer, ZCE order.

**Excluded**: receiving $5 (passive), holding balance (passive), sending $5 back to ambassador (cycling — Nash anti-fraud filter).

### Timing Analysis (Iteration 4)

`recipient_timing_query()` finds each recipient's first qualifying activity timestamp. Uses per-type first-timestamp CTEs (CN send, card, BT, ZCE) → `union all` → `row_number()` to pick earliest. Uses `claimed_at` (full timestamp) as t=0.

Key finding: median time to first activity is ~43 minutes. 100% of engaged recipients act within 24 hours. Revisit rule: check after 1 day, give up after 2.

### Data Source

Reads `recipient_overview`, `note_distribution`, `recipient_activity`, `ambassador_summary`, `app_opens`, `recipient_timing`, and `app_opens_detailed` arrays from a cache JSON file. The `queries.py` file contains the canonical SQL for fetching this data via Rube MCP (Metabase database ID 1). App opens data is sourced from Amplitude (see Rube MCP notes below). `app_opens_detailed` contains per-event timestamps with `hours_after_demo` for brand recall analysis (Iteration 5).

### Visit Sheet Enrichment (Iteration 6)

`recipient_overview` entries can be enriched with `business_name`, `location_lat`, and `location_lng` from the ambassador visit log Google Sheet (`1bFf0NAQFFXIYYxMC1yJeqowRz6MwT_-xawZeg5H9wUQ`, tab "Form Responses 1"). Matching is done on normalized phone number (strip non-digits). Only updates `business_name` where currently null. The Revisit Targets table shows a "Location" column with clickable Google Maps links and a "Download CSV" button.

## DB Schema Knowledge

Accumulated from iterations 1-4 of Demo Dollars analysis.

### Ambassador ID → Name Mappings

| User ID | Username | Real Name |
|---------|----------|-----------|
| `019bfeae-4ab6-77ef-8fe5-7fb91c7755ce` | `user_1ef1d1ea` | Arslan Ansari |
| `019c22a1-07a6-7c67-889e-5c655fe8ae11` | `owaisferoz1` | Owais Feroz |
| `a9519a82-c510-4b5b-a24b-ecec3f68de23` | `muhammadzahid` | Muhammad Zahid |

### Schema Facts

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

### Shared CTE Pattern

All demo dollars queries share two CTEs defined in `queries.py`:
- `_ambassadors_cte()` — users with ambassador role, excluding `EXCLUDED_IDS`
- `_demo_dollars_cte()` — cash notes from ambassadors to same-day-created recipients (Feb 1+), no amount filter

## Rube MCP (Composio) Notes

### Metabase (SQL Queries)
- Tool: `METABASE_POST_API_DATASET` with `database: 1`, `type: "native"`, `native: {query: "..."}`
- Connection is active and works via both `RUBE_MULTI_EXECUTE_TOOL` and workbench
- Session ID: `"each"` (pass in all subsequent meta tool calls)

### Amplitude (App Analytics)
- Tools: `AMPLITUDE_FIND_USER` (UUID → amplitude_id), `AMPLITUDE_GET_USER_ACTIVITY` (event stream)
- **Critical**: These tools FAIL via `RUBE_MULTI_EXECUTE_TOOL` (routes to `api2.amplitude.com` which is the ingestion API, returns 404)
- **Workaround**: Use `run_composio_tool()` inside `RUBE_REMOTE_WORKBENCH` — this routes correctly and works
- Workflow: batch `AMPLITUDE_FIND_USER` to get amplitude_ids → batch `AMPLITUDE_GET_USER_ACTIVITY` to get events → count `session_start` events for app opens
- Event types for app opens: `"app_open"`, `"session_start"`, `"[Amplitude] Start Session"`, `"App Open"`, `"app_opened"`
- 28 of 32 demo dollar recipients were found in Amplitude (4 never opened the app at all)

### Cache JSON Workflow

1. Write/update SQL in `queries.py` (canonical source of truth)
2. Run query via `METABASE_POST_API_DATASET` → extract `rows` from `data.data.rows`
3. Map column names from `data.data.cols[].name` to build JSON objects
4. For Amplitude data: batch via `RUBE_REMOTE_WORKBENCH` using `run_composio_tool()`
5. Update local `*_cache.json` file with new/updated arrays
6. Run `python3 run.py --json *_cache.json` to regenerate HTML

## Glossary

**Nash**, **Terra**, and **Atlas** are agents in the Praxis repository (`/Users/asharib/Documents/GitHub/praxis/`):
- **Nash** — Game theory expert. Designs incentive systems where fraud is economically irrational using mechanism design, auction theory, and Nash equilibria. Stress-tests systems for exploits.
- **Terra** — Field sales expert and Ground Force coach. Stress-tests ambassador training materials and pitch flows by simulating real merchant/ambassador personas before they ship.
- **Atlas** — Data navigator. Writes SQL queries and retrieves insights from the ZAR database. Uses a Five Questions Framework (metric, entity scope, time, grouping, output format) before writing any query.
