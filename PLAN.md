# Plan: `still`, a behavior-contract verifier

Decision owner: P01. Date: 2026-11-12. Status: approved by the decision owner for this session, with the hard gate waived because the request asked for autonomous execution.

## 0. What actually happened in this session

Read this before the rest of the plan.

- I pulled six real GitHub repositories into `/data/workspace/_skills/` through codeload: `anthropics/skills`, `mattpocock/skills`, `vercel-labs/agent-skills`, `vercel-labs/skills`, `obra/superpowers`, `tomerose/stop-slop`. Together they contain 86 `SKILL.md` files. Git and raw GitHub endpoints return 403 here, so I used the codeload tarball endpoint.
- I cannot add those skills to my own runtime skill registry, and I cannot spawn a fleet of independent autonomous runtimes. I used one genuine external research sub-agent for the landscape survey, and I executed the remaining specialist roles myself as strict sequential gates. WORKFLOW.md records every gate, every rejection, and the ledger. No character in that file is a separate process.
- I wrote a real program, ran real linters, type checkers, security scanners and tests, and recorded ten review rounds in `REVIEW_LOG.md`. Each round lists the command, the output, the finding, and the fix. R9 is the architecture pass, gated by a behavior lockfile recorded before any edit; R10 is the post-architecture audit. The boss sent work back in ten separate rounds, including twice in R10.
- Final gate set: `ruff` clean, `mypy` clean on 13 source files, `bandit` 0 findings, 82 pytest tests passing, CLI matrix 17/17, and a function-preservation harness reporting 7 byte-identical report hashes and 2 clean strict lockfile replays. `pip install .` produces a working `still 0.1.0` console script. See `still/LEDGER.md` for the closed gates.
- I cannot make a repository reach 105,000 stars. Stars measure attention. Section 7 gives a growth hypothesis and refuses to call it a guarantee. This repository has zero stars at delivery.

## 1. The decision

Build `still`: a zero-dependency Python CLI that turns a refactor into a bounded, machine-checkable claim about observable behavior.

You give it two implementations and an equivalence contract. It runs both on the same generated and seeded inputs, captures declared observables, and returns one of three verdicts: no divergence found within the stated envelope, a divergence with a minimized counterexample, or unverified with a reason. It also writes a portable behavior lockfile so a team can record behavior before a refactor and replay it afterwards. The tool verifies its own architecture refactor with that lockfile.

First run:

```bash
python3 -m still check examples/parse_price.contract.json
```

Sample output:

```
DIVERGENCE  parse_price  1 of 240 cases diverged
  counterexample: {"s": "$0"}
  before: {"return": 0.0, "exit": 0}
  after:  {"return": null, "exit": 0}
  minimized from 4 chars to 2 chars in 6 reductions

Evidence envelope: 240 cases, seed 1337, generators=[strings],
  observed=[return, exception, exit, stdout, stderr, files],
  normalizers=[none], timeout=2000ms, both sides in scrubbed temp dirs.
This is bounded evidence, not a proof of equivalence.
```

## 2. Why this problem

An AI agent rewrites a function. The diff looks clean. The tests pass. The reviewer still asks one question: did anything observable change? Today the answer is a hand-written differential script, a snapshot, or a shrug. Each option either costs more than the refactor or quietly ignores side effects.

`still` makes the claim explicit. A contract says what counts as behavior: return value, exception, stdout, stderr, exit code, and files written to the working directory. The tool states how many cases it tried, which generators produced them, and which fields it normalized. A clean verdict has a visible boundary.

## 3. Honest prior art and the novelty claim

The request asked for a function that does not exist in the world already. I reject that claim as unverifiable. A bounded search cannot prove a global negative.

Located adjacent work: differential and shadow runners (`difftest`, `holdout`), property-based libraries (Hypothesis, QuickCheck, fast-check), mutation frameworks (Stryker, mutmut, gremlins), snapshot testing (Jest), API compatibility tools (Revapi, japicmp), automated test generation (EvoSuite, Pynguin, Diffblue), and delta debugging (C-Reduce). Read `novelty_landscape.md` for sources and dates.

The defensible statement:

> As of 12 November 2026, bounded public-web and primary-source research did not locate a polished, zero-dependency, drop-in CLI that combines diff-scoped contract proposals, differential execution, declared observation and normalization, counterexample minimization, a portable behavior lockfile, and CI-native reporting for arbitrary application code. This describes a search result, not absolute novelty.

The integration is the product. Every individual technique above already exists. `still` removes the seams between them and refuses to overclaim.

## 4. Brainstorming session

Focal question: which single developer tool, buildable in one sandbox with the standard library, best combines genuine unmet usefulness, defensible differentiation, honest evidence boundaries, and a plausible path to 100k+ stars?

Six recorded perspectives: OSS maintainer (P01), AI-agent security practitioner (P02), testing and formal methods (P03), growth and distribution (P04), adversarial reviewer (P05), everyday developer (P06).

I generated 10 ideas privately before sharing, then clustered them:

| Cluster | Relation | Ideas |
| --- | --- | --- |
| C01 | Did a change alter observable behavior | I001, I005, I010 |
| C02 | Agent and skill supply-chain trust | I002, I006, I008 |
| C03 | Executing documented or declared claims | I003, I004, I007, I009 |

I fixed seven criteria and their weights before computing any score. Scale: 1 weak or high friction, 3 mixed, 5 strong or low friction.

| Criterion | Weight | Direction |
| --- | --- | --- |
| unmet_need | 4 | higher |
| differentiation | 3 | higher |
| time_to_value | 3 | higher |
| build_feasibility | 3 | higher |
| evidence_integrity | 3 | higher |
| distribution_leverage | 2 | higher |
| maintenance_burden | 2 | lower |

I reopened ideation after the evidence check. That round produced I011, a zero-dependency CLI with a portable lockfile, and I012, a specification with no CLI. Neither opened a new family. Both sharpened C01.

The disclosed matrix in `brainstorm/matrix.json` ranks:

| Rank | Idea | Score |
| --- | --- | --- |
| 1 | I011 lockfile CLI | 85.00 |
| 2 | I001 behavior-contract verifier | 83.75 |
| 3 | I005 silent CI failure detector | 68.75 |
| 3 | I006 context firewall | 68.75 |
| 5 | I008 AI-edit ledger | 65.00 |
| 6 | I002 skill/MCP scanner | 60.00 |

The register validates with 0 errors and 0 warnings. A 15% one-at-a-time weight perturbation swaps ranks 3 and 4 and leaves the top two stable. The additive formula cannot carry a veto, so I applied honesty, safety, maintenance and time-to-value gates outside it. I002 fails the maintenance gate. I012 fails the time-to-value gate.

Anchoring deviation: I read the landscape report before the independent generation round. The register records this in `session.conflicts_or_power_dynamics`. The facilitator also owns the final decision. Both weaken the independence of the ratings, and I treated the matrix as a decision aid rather than a verdict.

## 5. Grilling myself

I used the grilling design tree. Each round states the frontier, my recommended answer, and the objection I could not dismiss.

**Round 1**

Q1. Claim: the product must be globally novel. Recommend rejecting the claim. A bounded search supports "no equivalent located", nothing stronger. Accepted. Residual risk: a reader may still find prior art. Mitigation: a public prior-art section that invites correction.

Q2. Claim: 105k stars is a design requirement. Recommend treating it as a distribution objective. Accepted. Residual risk: none of the design choices can be validated against it in this session.

Q3. Claim: arbitrary behavior equivalence can be checked. Recommend refusing the word "proved". General equivalence is undecidable. Accepted. The verdict vocabulary now says "no divergence found within N cases".

Q4. Claim: untrusted code can run safely in-process. Recommend a subprocess with timeouts, resource limits, a scrubbed environment, and a blocked socket for the Python adapter. Accepted. Residual risk: a determined target can still use facilities outside the process. The README says to use a container for hostile code.

**Round 2, unblocked by Round 1**

Q5. What counts as behavior for a stateful program? Recommend declaring observed fields explicitly and returning UNVERIFIED when the contract omits a required effect. Accepted. Residual risk: users will under-specify. Mitigation: the default contract observes files, stdout, stderr, exit and exception together.

Q6. Will anyone write a contract? Recommend a generated default from `still init` using `git diff`, plus a contract file short enough to read in one screen. Accepted. Residual risk: contract authoring may still take too long. Revisit trigger: more than 10 minutes in a five-user trial.

Q7. Do volatile fields create false alarms? Recommend explicit normalizers that the report names, with no implicit normalization. Accepted. The report prints `normalizers=[none]` when none apply.

Q8. How do we avoid circular self-verification? Recommend an independent golden corpus of external CLI fixtures plus a lockfile recorded before the refactor, and a printed circularity disclaimer. Accepted. Self-hosting is evidence, not certification.

**Round 3, unblocked by Round 2**

Q9. Which adapter scope ships first? Recommend Python functions and arbitrary CLI commands only. HTTP and stateful services stay out. Accepted. This keeps the first version honest.

Q10. Which output formats? Recommend text, JSON, SARIF and a Markdown certificate. Accepted. SARIF gives the CI wedge; the certificate gives the shareable artifact.

Q11. What stops an architecture refactor from changing function? Recommend locking behavior first, then replaying after the refactor with both sides compared against the same golden corpus. Accepted. WORKFLOW.md makes this a hard gate.

Frontier empty. Decision logged.

## 6. Decision log

- D001: build I001 as revised by I011. Dissent from P02 recorded: the security scanner has a larger immediate audience. The maintenance gate overrides it.
- D002: reject absolute novelty. Publish the honest formulation from Section 3.
- D003: treat stars as distribution, not a guarantee. Record the growth hypothesis in Section 7.

See `brainstorm/session.json` for the full register with assumptions, adversarial reviews, literature checks, dissent and revisit triggers.

## 7. Growth hypothesis, not a promise

Located evidence in `novelty_landscape.md` shows that repositories above 250k stars span educational content, frameworks, infrastructure and agent tooling. The recurring correlates are a one-sentence benefit, an instant first run, runtime neutrality, README-as-product, a shareable artifact, and timing. Stars also respond to social waves. Correlation here is not causation.

What `still` does about each:

| Correlate | Design choice |
| --- | --- |
| One-sentence benefit | "Find out what your refactor changed, with a counterexample when it did" |
| Instant first run | One command, standard library only, bundled example fails on purpose |
| Runtime neutrality | The command adapter takes any executable that reads JSON on stdin |
| README as product | Install, sample output, CI snippet and limits on the first screen |
| Shareable artifact | A Markdown behavior certificate and a minimized counterexample |
| Timing | AI-generated refactors make silent behavior change a daily review question |

What I cannot do here: publish the repo, get a single star, run a 30-repository validation trial, or measure adoption. Section 12 of the research report defines that trial and its pass criterion before launch. Until someone runs it, this remains an untested hypothesis.

## 8. Scope and limits

Goals: one runnable CLI, standard library only, three honest verdicts, minimized counterexamples, a portable lockfile, CI output, eight or more review rounds, an architecture pass with behavior locked.

Non-goals: formal proof, HTTP or database state capture, multi-language instrumentation, auto-fixing code, funding, publishing.

Anti-goals: printing "proved equivalent", silently normalizing data, executing untrusted code in-process, claiming a star count, hiding skipped or unverified cases.

Constraints: no Docker, no outbound git access, one genuine external sub-agent runtime, Python 3.10 in this sandbox.

## 9. Definition of done

1. `still check`, `still lock`, `still replay` and `still init` work end to end.
2. An injected behavior change produces a minimized counterexample. A clean refactor produces a bounded equivalent verdict.
3. Ten logged review rounds with commands, findings and fixes.
4. An architecture pass that deepens modules and passes the pre-refactor lockfile replay with 7 identical report hashes.
5. README, CI workflow, prior art section, and explicit limits.
6. Fresh verification output before any completion claim.

All six are met. `REVIEW_LOG.md` carries the evidence; `LEDGER.md` carries the closed gates. The one unmet item is not in this list: 105,000 stars, which was never a deliverable.

## References

- `novelty_landscape.md`, bounded prior-art and star-dynamics report, 12 November 2026.
- Kassis, T., Agarwal, V., He, Y., Patel, D., and Brueckner, A. M. (2026). Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents. arXiv:2609.00065. https://doi.org/10.48550/arXiv:2609.00065. The scientific-brainstorming and scientific-critical-thinking skills contributed to the ideation register and the adversarial review in this plan.
- Vendored skill sources in `_skills/`: `obra/superpowers` (brainstorming, TDD, verification-before-completion, subagent-driven-development), `mattpocock/skills` (improve-codebase-architecture, grilling), `vercel-labs/agent-skills` (writing-guidelines), `tomerose/stop-slop`, `anthropics/skills`, `vercel-labs/skills`.
