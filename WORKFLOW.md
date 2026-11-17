# Workflow, agent charters and quality gates

Boss and manager: the session controller (P01). Every gate below has a named owner, an input, an output contract, and rejection criteria. The controller signs off or sends the work back. No gate closes on a self-report alone.

## 0. Execution model

One genuine external sub-agent exists in this environment, used for the prior-art and star-dynamics survey. The remaining roles are charters that the controller executes in strict sequence, with an isolated brief per role and a written verdict per gate. This is a real difference from a fleet of independent runtimes. REVIEW_LOG.md and the ledger below show what each gate actually produced.

The controller keeps a ledger at `still/LEDGER.md`. Each line records: gate, owner, verdict, evidence command, and ruling when a conflict appeared. Rulings follow the pattern `Ruling: <decision> - <reason> - <cost if wrong>`.

## 1. Agent charters

| ID | Role | Input | Output contract | Rejection criteria |
| --- | --- | --- | --- | --- |
| A1 | Scout | List of named GitHub repos, prior-art questions | Vendored repos in `_skills/`, `novelty_landscape.md` with dated sources | Missing repos, invented URLs, unlabeled speculation |
| A2 | Ideator | Focal question, six perspectives | `brainstorm/session.json` with independent ideas, assumptions, provenance | Ideas with no uncertainty, no provenance, or post-hoc criteria |
| A3 | Inquisitor | Shortlist, design tree | Grilling rounds with recommended answers, objections, residual risk | An unanswered frontier question, a claim of proof, a hidden assumption |
| A4 | Architect | Approved decision, prior art | `PLAN.md`, spec, glossary, ADRs | Overpromising novelty, missing non-goals, missing honesty boundary |
| A5 | Implementer | Spec, module briefs | Source modules that satisfy the tests | Code before a failing test, missing error paths, undeclared global state |
| A6 | Test engineer | Spec, public interfaces | pytest suite with red-green evidence | Tests that pass on first run, mocks replacing real behavior, missing edge cases |
| A7 | Security auditor | Source tree, threat model | Findings with severity and fix | Unisolated execution, unbounded output, path traversal, implicit trust |
| A8 | Reviewer | Each review round brief, full diff | Round entry in REVIEW_LOG.md with command output | Round with no command, no finding, or a fixed claim without fresh output |
| A9 | Architecture refactorer | Locked behavior, GLOSSARY.md, ADRs | Deepened modules, before and after diagrams, replay verdict | Any behavior delta, shallow module left unexplained, missing equivalence evidence |
| A10 | Release | Verified tree | README, CI, LICENSE, delivery bundle | README without limits, missing CI, unverified success claims |

## 2. Gates

| Gate | Owner | Closes when | Boss action on failure |
| --- | --- | --- | --- |
| G0 Environment | A1 | All six repos vendored; QA toolchain installed | Retry with an alternate endpoint; record the 403 on git and raw hosts |
| G1 Research | A1 | Report dated, sources labeled, absolute novelty rejected | Reject and re-run the survey |
| G2 Ideation | A2 | Register validates with 0 errors, criteria fixed before scoring | Reject; recompute with pre-declared weights |
| G3 Grill | A3 | Frontier empty, every residual risk named | Reject; reopen the branch |
| G4 Design | A4 | Plan has goals, non-goals, anti-goals, honest novelty text | Reject; rewrite the section |
| G5 Implementation | A5, A6 | Tests fail for the right reason, then pass; whole suite green | Send the module back. Log the rejection. |
| G6 Security | A7 | No critical or high finding; every medium has a fix or a ruling | Send back. No exceptions. |
| G7 Review rounds | A8 | Ten rounds each with a real command, finding and fix | Reject the round; re-run it. A round that finds nothing must say so and show the command. |
| G8 Architecture | A9 | Lockfile replay reports no divergence; 7 report hashes identical; no public behavior changed | Revert the refactor and redo it |
| G9 Release | A10 | Fresh verification output attached to every claim | Reject the completion claim |

## 3. Strictness rules

1. Evidence before claims. A gate needs the command output in the same round. "Should pass" never closes a gate.
2. Rejection is cheap. A module that misses an error path goes back to A5 with the finding attached, not with a note to fix it later.
3. No silent discards. The controller adjudicates a disputed finding only at the fix-loop cap, and writes a ruling into the ledger.
4. No scope drift. A round reviews its assigned surface. New findings on untouched code go to the ledger, not into the current round's fix list.
5. No fake completeness. A round that finds nothing records the exact command and the clean output. An empty finding list without evidence is a rejected round.
6. Function preservation is a hard gate. G8 uses a behavior lockfile recorded before any architecture edit and replays it afterwards.

## 4. Review round assignments

| Round | Lens | Primary command |
| --- | --- | --- |
| R1 | Static lint and dead code | `ruff check` |
| R2 | Type and interface correctness | `mypy` |
| R3 | Security and unsafe execution | `bandit`, manual threat review |
| R4 | Unit and regression behavior | `pytest` |
| R5 | Malformed input and robustness | adversarial pytest cases, fuzz script |
| R6 | CLI contract and exit codes | end-to-end CLI matrix |
| R7 | Resource limits and runaway processes | timeout, output cap, process-group kill tests |
| R8 | Dogfooding, docs and CI | `still lock` and `still replay`, README and CI review |
| R9 | Architecture deepening | `still replay` against the pre-refactor lockfile |
| R10 | Post-architecture audit and final closure | stale-reference scan, full gate set, preservation harness |

Rounds R1 through R10 must each produce at least one logged finding or a documented clean command. The controller rejects any round that claims a pass without fresh output. R10 found two invalid fixtures in a newly added test and sent it back twice.

## 5. Architecture pass contract

The pass follows `improve-codebase-architecture` from `mattpocock/skills`: scope to recently changed hot spots, read `GLOSSARY.md` and ADRs, apply the deletion test to suspected shallow modules, present ranked candidates with before and after diagrams, then grill the chosen candidate.

Vocabulary enforced in the report: module, interface, depth, seam, adapter, leverage, locality. Banned words in the report: component, service, API, boundary.

Hard constraint from the request: the refactor must not change any function of the program. The controller records a behavior lockfile over the public surface before touching a file, applies only deepening edits, then replays. A divergence reverts the pass.

## 6. Writing standard

Docs follow `stop-slop` and the Vercel `writing-guidelines` checks that are available offline: no throat-clearing openers, no binary-contrast templates, no filler adverbs, no em dashes, active voice, specific claims, varied rhythm. The README states limits on the first screen.

## 7. Ledger extract

Ledger entries are appended as work completes. The authoritative file is `still/LEDGER.md`. Rejected work keeps its entry so the boss can see the rework rather than only the final state.
