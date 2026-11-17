# Context

Project: still. Purpose: bounded, machine-checkable evidence about what a refactor changed.

## Decisions that bind later work

1. A verdict describes a bounded corpus. The tool never claims proof of equivalence.
2. Normalization is declared in the contract and appears in the report. No implicit cleanup.
3. Every case runs in a fresh subprocess with a scrubbed environment and resource limits.
4. The `command` adapter carries no in-child network guard. The README states this limit.
5. Lockfiles record behavior before a refactor. Replay after a refactor is evidence, not certification.

## Architecture vocabulary

Use module, interface, depth, seam, adapter, leverage and locality. See `GLOSSARY.md` for domain terms.

## Change hot spots

`cli.py` holds three thin adapter loops. `evidence.py` is the deep claim module behind them. `execution.py` holds the isolated runner. `report.py` holds output formats. Review rounds in `REVIEW_LOG.md` record what changed in each; `LEDGER.md` holds the closed gates.

## ADRs

- [0001 Evidence, not proof](docs/adr/0001-evidence-not-proof.md)
