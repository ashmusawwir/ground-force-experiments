# Ground Force Experiments

Standalone experiment tracking for Zar's ground force (field ambassador) team. Each directory is one experiment or dashboard.

See [`CLAUDE.md`](CLAUDE.md) for full conventions, run commands, DB schema, and Notion page IDs.

---

## Experiment Catalog

| ID | Directory | Pattern | What it tests |
|----|-----------|---------|---------------|
| EXP-000 | `exp-000-merchant-network/` | B | Merchants as user-acquisition channel — CAC and retention analysis |
| EXP-001 | `exp-001-show-dont-tell/` | A | Demo-first opener vs verbal pitch |
| EXP-002 | `exp-002-social-proof-map/` | A | Showing nearby-merchant map at opener |
| EXP-004 | `exp-004-merchant-activation/` | B (queries only) | Tiered cash incentive to activate dormant merchants |
| EXP-006 | `exp-006-question-redirect/` | A | Universal redirect phrase for Q→Demo |
| EXP-007 | `exp-007-demo-dollars/` | A | Post-demo retargeting — do revisited merchants convert higher |
| EXP-008 | `exp-008-gold-market-research/` | C | Merchant demand for digital gold |
| EXP-009 | `exp-009-demo-shadow/` | C | Observational shadow of ambassador demos to identify execution gaps |
| EXP-010 | `exp-010-channel-yield/` | C | Which sourcing channels produce hires + flyer optimization |
| EXP-011 | Notion-only | C | Growth Partner Referrals |
| EXP-012 | Notion-only | C | University Students Outreach |
| — | `deprecated/exp-009-directed-day/` | B | Structured daily task lists *(deprecated, was EXP-009)* |
| — | `deprecated/exp-018-direct-to-training/` | C | Direct-to-training hiring sprint *(deprecated)* |
| — | `deprecated/exp-020-ramadan-timing/` | A | Ramadan visit timing *(deprecated)* |

## Architecture Patterns

- **Pattern A** — Sheet-based funnel: `run.py` → terminal table + HTML report
- **Pattern B** — SQL + cache JSON → self-contained HTML dashboard
- **Pattern C** — Markdown-only design doc / experiment brief

## Running Experiments

```bash
# Pattern A
cd exp-001-show-dont-tell && python3 run.py

# Pattern B (requires cache JSON from Rube MCP)
cd exp-007-demo-dollars && python3 run.py --json demo_dollars_cache.json
```

## Shared Library

[`lib/`](lib/) — shared SQL helpers and central query registry:
- `lib/sql.py` — exclusion lists, CTE generators
- `lib/queries.py` — every SQL query in the repo, importable from one place
- `lib/verify_report.py` — Notion report verification utility

## Docs

[`docs/`](docs/) — project-level reference documents:
- `Experimentation-OS.md` — experiment report structure and writing rules
