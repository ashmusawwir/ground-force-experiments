# Ground Force Experiments

Standalone experiment tracking for Zar's ground force (field ambassador) team. Each subdirectory is one experiment.

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

## Glossary

**Nash**, **Terra**, and **Atlas** are agents in the Praxis repository (`/Users/asharib/Documents/GitHub/praxis/`):
- **Nash** — Game theory expert. Designs incentive systems where fraud is economically irrational using mechanism design, auction theory, and Nash equilibria. Stress-tests systems for exploits.
- **Terra** — Field sales expert and Ground Force coach. Stress-tests ambassador training materials and pitch flows by simulating real merchant/ambassador personas before they ship.
- **Atlas** — Data navigator. Writes SQL queries and retrieves insights from the ZAR database. Uses a Five Questions Framework (metric, entity scope, time, grouping, output format) before writing any query.
