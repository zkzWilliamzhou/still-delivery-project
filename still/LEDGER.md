# Gate ledger

Format: `Gate | Owner | Verdict | Evidence | Ruling`.

Every gate is closed. "PASS" means the boss re-ran the named command on the
final tree and kept the output. Rejected work keeps its entry.

| Gate | Owner | Verdict | Evidence | Ruling |
| --- | --- | --- | --- | --- |
| G0 Environment | A1 | PASS | Six repos vendored in `_skills/` (1,330 files); `ruff/mypy/pytest/bandit` installed | Ruling: git and raw GitHub return 403 here, use codeload tarballs. Cost if wrong: none, contents verified by file count |
| G1 Research | A1 | PASS | `novelty_landscape.md` with dated sources and explicit search limits | Ruling: reject absolute novelty. Cost if wrong: a reader finds prior art and the README invites correction |
| G2 Ideation | A2 | PASS | `brainstorm/validation.json` reports 0 errors, 0 warnings | Ruling: criteria fixed before scoring. Cost if wrong: rating bias remains visible in `session.json` |
| G3 Grill | A3 | PASS | `PLAN.md` Section 5, three rounds, frontier empty | Ruling: self-verification stays evidence, not certification |
| G4 Design | A4 | PASS | `PLAN.md` with goals, non-goals, anti-goals, honest prior art | Ruling: 105k stars is a distribution objective, not a guarantee |
| G5 Implementation | A5, A6 | PASS | `pytest tests -q` -> 82 passed; `scripts/cli_matrix.py` -> 17/17 | Ruling: no mock replaces real behavior; injected divergence yields a minimized counterexample |
| G6 Security | A7 | PASS | `bandit -q -r src/still` -> 0 findings; `tests/test_resources.py` -> 9 passed | Ruling: B607 fixed by an absolute git resolver, not by suppression. Cost if wrong: PATH becomes a trust input again |
| G7 Review rounds | A8 | PASS | `REVIEW_LOG.md`, ten rounds, each with command, output, finding and fix | Ruling: R1's per-line output lives in an earlier turn; the final tree was re-linted fresh. Cost if wrong: an old finding is unrecoverable in detail |
| G8 Architecture | A9 | PASS | `scripts/verify_function_preservation.py verify` -> 7 identical report hashes, 2 clean strict replays | Ruling: C2 deferred (one adapter makes a hypothetical seam), C3 rejected (deletion test). No observable function changed |
| G9 Release | A10 | PASS | README with limits, CI workflow, LICENSE, installed `still 0.1.0`, full final gate set | Ruling: zero stars at delivery; the star objective is a hypothesis in PLAN Section 7 |

## Rework recorded by the boss

| Round | What was sent back | Why | Outcome |
| --- | --- | --- | --- |
| R1 | First lint pass | 21 findings, one functional defect | Fixed, re-linted |
| R2 | `mypy` failure | Stale cache looked like an internal error; isolation found the real type defect | `inputs.py` fixed, 11 files clean |
| R3 | First bandit pass | 10 LOW findings | Absolute git path, `shell=False`, path confinement; 0 findings |
| R4 | Failing test | Test asserted the wrong dedupe semantics | Test corrected and a real cap test added |
| R5 | CLI override surface | Bounds bypassed; normalizer and lockfile gaps | Four fixes and 19 adversarial tests |
| R6 | README sample | Invented output | Replaced with literal CLI output; CLI matrix added |
| R7 | Two resource tests | Test-authoring mistakes, not program defects | Rewritten to actually time out and create 200 files |
| R8 | `pip install .` | `UNKNOWN-0.0.0` wheel on setuptools 59.6.0 | `setup.py` shim, modern license field, stale egg-info removed |
| R9 | Architecture report | Needed a hard function-preservation gate before edits | Baseline recorded, C1 applied, replay clean |
| R10 | `tests/test_evidence.py` | Two invalid fixtures, sent back twice | Fixed to `strip` and `["stderr"]`; 82 tests pass |

## Standing constraints

1. Evidence before claims. A gate needs command output from the same round.
2. Rejection is cheap and logged, not deferred.
3. No silent discards, no scope drift, no fake completeness.
4. Function preservation is a hard gate: a divergence reverts the refactor.
5. ADR-0001 stays closed: every verdict states its bounded evidence.

`Ruling: <decision> - <reason> - <cost if wrong>`.
