# Ground Force Experiments

Standalone experiment tracking for Zar's ground force (field ambassador) team. Each directory is one experiment or dashboard.

See [`CLAUDE.md`](CLAUDE.md) for full conventions, run commands, DB schema, and Notion page IDs.

---

## Experiment Catalog

| ID | Directory | Pattern | What it tests |
|----|-----------|---------|---------------|
| EXP-000 | Notion-only | C | Merchants as user-acquisition channel — CAC and retention analysis |
| EXP-001 | `exp-001-show-dont-tell/` | A | Demo-first opener vs verbal pitch |
| EXP-002 | `exp-002-social-proof-map/` | A | Showing nearby-merchant map at opener |
| EXP-004 | `exp-004-merchant-activation/` | B (queries only) | Tiered cash incentive to activate dormant merchants |
| EXP-006 | `exp-006-question-redirect/` | A | Universal redirect phrase for Q→Demo |
| EXP-007 | `exp-007-demo-dollars/` | B | What demo-dollar recipients did |
| EXP-008 | `exp-008-gold-market-research/` | C | Merchant demand for digital gold |
| EXP-009 | `deprecated/exp-009-directed-day/` | B | Structured daily task lists with geo-clustered visits *(deprecated)* |
| EXP-010 | `exp-010-demo-shadow/` | C | Observational shadow of ambassador demos to identify execution gaps |
| EXP-011–017 | Notion-only | C | See CLAUDE.md |
| EXP-018 | `exp-018-direct-to-training/` | C | Direct-to-training hiring sprint |
| EXP-019 | `exp-019-channel-yield/` | C | Which sourcing channels produce hires |
| EXP-020 | `exp-020-ramadan-timing/` | A | Ramadan visit timing: daytime vs post-Taraweeh nighttime |
| — | `merchant-user-onboardings/` | B | Merchant onboarding, activation, retention dashboard |

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
