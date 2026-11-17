# ADR 0001: Report bounded evidence, never proof

Date: 2026-11-12. Status: accepted.

## Decision

`still` reports `NO_DIVERGENCE_FOUND`, `DIVERGENCE` or `UNVERIFIED`. It never says "proved equivalent". Every report carries an evidence envelope naming the cases run, generators, seed, timeout, observed fields, normalizers and allowed divergences.

## Reason

General behavior equivalence is undecidable. A corpus of generated and seeded inputs gives evidence about the cases tried. A clean verdict that hides its boundary invites readers to treat it as a guarantee, which is the failure mode the tool exists to prevent.

## Consequences

- Verdict text and JSON both carry a disclaimer.
- UNVERIFIED has its own exit code, so CI cannot confuse a skipped case with a pass.
- Adding a new generator or observable changes the envelope and therefore the claim.
- Prior art in `novelty_landscape.md` frames the same boundary.

## Rejected alternative

Report a boolean "equivalent" flag. Rejected because it hides the coverage and makes false confidence the default output.
