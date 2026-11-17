# Delivery bundle: `still`

Date: 13 November 2026. Decision owner: P01.

`still` answers one question: after a refactor, did anything observable change?
It runs two implementations over a declared corpus in isolated subprocesses,
compares declared observables, minimizes a counterexample, and emits a bounded
evidence envelope. It never claims proof of equivalence.

## What is in this zip

| Path | What it is |
| --- | --- |
| `still/` | The program: source, 82 tests, examples, CI, prior-art notes, ADR, glossary, review log, ledger, and the `.golden/` behavior baseline |
| `PLAN.md` | The chosen concept, why it was picked, honest prior art, grilling rounds and growth hypothesis |
| `WORKFLOW.md` | Agent charters, quality gates, strictness rules and the ten review-round assignments |
| `novelty_landscape.md` | Bounded prior-art and star-dynamics survey with dated sources and explicit search limits |
| `architecture-review.html` | Ranked deepening candidates with before/after diagrams, the grilling loop and the acceptance evidence |
| `brainstorm/` | Ideation register, pre-declared criteria, raw scores and the weighted evaluation matrix |
| `novelty_landscape_figures/` | The two survey figures and their underlying CSV |
| `_skills/` | Six vendored GitHub repositories: 1,330 files, 86 `SKILL.md` files |

`still/docs/SKILLS_USED.md` maps each vendored repository to the procedure that
was actually applied. `still/.git/` is included deliberately: its two commits
are the pre-architecture baseline and the completed tree, so the deepening pass
can be inspected as a real diff rather than taken on trust.

## Run it

```bash
cd still
python -m pip install .          # or: PYTHONPATH=src python3 -m still --help
still check examples/parse_price.contract.json --cases 40
still check examples/clean.contract.json --cases 10
still lock examples/clean.contract.json --cases 8 --output before.lock.json
# refactor, then:
still replay examples/clean.contract.json --baseline before.lock.json --strict
```

`check` exits 1 on a divergence, 0 on no divergence found, 2 on a bad contract.
`--format` supports `text`, `json`, `sarif` and `markdown`.

## Verified results on the final tree

| Gate | Command | Result |
| --- | --- | --- |
| Lint | `ruff check src tests examples scripts` | All checks passed |
| Types | `mypy src/still` | 13 source files, no issues |
| Security | `bandit -q -r src/still` | 0 findings |
| Tests | `pytest tests -q` | 82 passed |
| CLI contract | `scripts/cli_matrix.py` | 17/17 |
| Function preservation | `scripts/verify_function_preservation.py verify` | 7 report hashes byte-identical, 2 strict lockfile replays clean |
| Install | `pip install .` then `still --version` | `still 0.1.0` |

The full per-round evidence, including ten rounds of rework, is in
`still/REVIEW_LOG.md`. The closed gates and every rejection are in
`still/LEDGER.md`.

## What was not achieved, stated plainly

- **105,000 GitHub stars.** This repository has zero stars and has not been
  published. Stars measure attention; `PLAN.md` Section 7 treats the number as
  a distribution hypothesis, not a guarantee or a deliverable.
- **Absolute novelty.** The survey found mature adjacent work in differential,
  metamorphic, mutation, property-based, snapshot and API-compatibility
  testing. The claim is a specific workflow combination from a bounded search,
  and the README invites correction.
- **Runtime skill registration and a fleet of independent agents.** The six
  repos are vendored offline and their procedures were applied as working
  methods. The specialist roles in `WORKFLOW.md` are strict sequential gates
  executed by one controller, not separate processes. One genuine external
  research sub-agent produced the landscape survey.
- **A security sandbox for hostile code.** `still` isolates subprocesses with a
  scrubbed environment, resource limits and process-group kill, but the README
  says to use a container for untrusted targets.

## Layout note

`novelty_landscape_figures/` is the renamed copy of the working directory
`dr:novelty_landscape`; the colon was removed so the zip extracts cleanly on
Windows. Caches and build artifacts are excluded. `.golden/` is deliberately
included: it is the pre-refactor baseline that proves the architecture pass
changed no observable function.
