"""Build a reproducible, evidence-aware brainstorming register for the `still` project.

No network and no LLM calls. All ratings are explicit, human-authored decisions
recorded here so the matrix can be re-run and audited.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
OUT.mkdir(parents=True, exist_ok=True)

PARTICIPANTS = {
    "P01": "OSS maintainer / developer-experience",
    "P02": "AI-agent practitioner / supply-chain security",
    "P03": "Testing and formal-methods engineer",
    "P04": "Open-source growth and distribution",
    "P05": "Adversarial reviewer / red team",
    "P06": "Everyday application developer",
}

CRITERIA = [
    ("unmet_need", 4, "higher", "Frequency and severity of the pain for a broad developer audience"),
    ("differentiation", 3, "higher", "Defensible separation from prior art located in the bounded landscape search"),
    ("time_to_value", 3, "higher", "Minutes from install to a first result a developer would act on"),
    ("build_feasibility", 3, "higher", "Correctly buildable in one sandbox with the Python standard library"),
    ("evidence_integrity", 3, "higher", "The tool can state its own evidence boundary without overclaiming proof"),
    ("distribution_leverage", 2, "higher", "Shareable output, runtime neutrality, README-as-product, trend alignment"),
    ("maintenance_burden", 2, "lower", "Ongoing churn from fast-moving vendor APIs, formats, or adversarial rule lists"),
]

# idea_id -> {criterion: (score, low, high), ...} plus qualitative fields
IDEAS = [
    dict(
        id="I001",
        statement=(
            "A language-neutral behavior-contract verifier: declare what observable "
            "behavior must survive a refactor, run old and new implementations on "
            "generated and seeded inputs, emit a bounded equivalence verdict, a "
            "minimized counterexample, and a CI-readable report."
        ),
        origin="ai-assisted", stage="independent", contributors=["P01", "P03"],
        assumptions=["A001", "A003", "A005"],
        predictions=[
            "For an injected behavior-changing refactor, at least one divergence is found within 500 cases",
            "Delta debugging shrinks the failing input below its original size",
        ],
        uncertainties=[
            "Whether users will write an equivalence contract at all",
            "Whether side-effecting systems can be scoped honestly",
        ],
        evidence_status="mixed", status="advanced-to-review",
        review="Best balance of measurable value and control over the evaluation protocol",
        scores=dict(unmet_need=(5,4,5), differentiation=(4,3,5), time_to_value=(4,3,5),
                    build_feasibility=(4,3,5), evidence_integrity=(5,4,5),
                    distribution_leverage=(4,3,5), maintenance_burden=(2,1,3)),
    ),
    dict(
        id="I002",
        statement=(
            "An end-to-end agent-skill and MCP supply-chain verifier that maps a skill "
            "to declared capabilities, file and network access, hidden instructions, "
            "and runtime behavior drift, then enforces a policy before install."
        ),
        origin="ai-assisted", stage="independent", contributors=["P02", "P05"],
        assumptions=["A002", "A006"],
        predictions=["Detects deliberately overprivileged skills in a held-out corpus"],
        uncertainties=["Vendor clients may bundle a free scanner", "Rule lists decay as attackers reword"],
        evidence_status="challenge-located", status="candidate",
        review="Urgent problem, weak moat; landscape already contains several scanners",
        scores=dict(unmet_need=(5,4,5), differentiation=(2,1,3), time_to_value=(4,3,5),
                    build_feasibility=(3,2,4), evidence_integrity=(3,2,4),
                    distribution_leverage=(5,4,5), maintenance_burden=(5,4,5)),
    ),
    dict(
        id="I003",
        statement=(
            "A README quickstart verifier that parses ordered install and usage claims, "
            "executes them in a declared clean environment, and distinguishes PASS, "
            "FAIL, SKIP and UNVERIFIED with an actionable location."
        ),
        origin="ai-assisted", stage="independent", contributors=["P01", "P06"],
        assumptions=["A001", "A004"],
        predictions=["Finds stale install commands in a sample of popular CLIs"],
        uncertainties=["README prose is not a formal specification", "Clean containers are expensive"],
        evidence_status="challenge-located", status="candidate",
        review="Clear UX story; kibble and doc-verify already occupy the workflow",
        scores=dict(unmet_need=(4,3,5), differentiation=(3,2,4), time_to_value=(3,2,4),
                    build_feasibility=(2,1,3), evidence_integrity=(4,3,5),
                    distribution_leverage=(4,3,5), maintenance_burden=(3,2,4)),
    ),
    dict(
        id="I004",
        statement=(
            "A dependency time machine that replays a project build against historical "
            "package versions to locate the exact release that introduced a behavior change."
        ),
        origin="ai-assisted", stage="independent", contributors=["P03", "P06"],
        assumptions=["A004"],
        predictions=["Bisects a seeded dependency regression to a single release"],
        uncertainties=["Historical package resolution often fails", "Slow on large graphs"],
        evidence_status="search-incomplete", status="candidate",
        review="Narrow audience; git bisect plus lockfiles already cover much of it",
        scores=dict(unmet_need=(3,2,4), differentiation=(4,3,5), time_to_value=(2,1,3),
                    build_feasibility=(2,1,3), evidence_integrity=(3,2,4),
                    distribution_leverage=(3,2,4), maintenance_burden=(4,3,5)),
    ),
    dict(
        id="I005",
        statement=(
            "A silent-failure detector for CI: find commands that exit zero while "
            "producing empty, truncated, or semantically wrong output, and attach a "
            "machine-readable assertion to each step."
        ),
        origin="ai-assisted", stage="independent", contributors=["P01", "P05"],
        assumptions=["A003"],
        predictions=["Flags a pipeline step that swallowed a failing subprocess exit code"],
        uncertainties=["Hard to define 'wrong' without a contract", "May duplicate shell linting"],
        evidence_status="search-incomplete", status="candidate",
        review="Cheap and useful but conceptually close to assertion-based testing",
        scores=dict(unmet_need=(4,3,5), differentiation=(4,3,5), time_to_value=(4,3,5),
                    build_feasibility=(4,3,5), evidence_integrity=(3,2,4),
                    distribution_leverage=(3,2,4), maintenance_burden=(2,1,3)),
    ),
    dict(
        id="I006",
        statement=(
            "A context firewall that scans files entering an LLM agent's context for "
            "zero-width characters, bidi controls, hidden instructions, secret-shaped "
            "strings, and token bombs, with a deterministic allow/deny report."
        ),
        origin="ai-assisted", stage="independent", contributors=["P02", "P06"],
        assumptions=["A002"],
        predictions=["Rejects a file with an injected bidi-hidden instruction"],
        uncertainties=["Unicode scanners already exist", "Character detection does not prove intent"],
        evidence_status="challenge-located", status="candidate",
        review="Easy to build, easy to copy, crowded prior art",
        scores=dict(unmet_need=(4,3,5), differentiation=(2,1,3), time_to_value=(5,4,5),
                    build_feasibility=(5,4,5), evidence_integrity=(3,2,4),
                    distribution_leverage=(4,3,5), maintenance_burden=(3,2,4)),
    ),
    dict(
        id="I007",
        statement=(
            "A reproducibility score and auto-fixer for any public repository: measure "
            "build determinism, pinned dependencies, and clean-environment install, then "
            "propose the smallest patch that raises the score."
        ),
        origin="ai-assisted", stage="independent", contributors=["P04", "P06"],
        assumptions=["A004"],
        predictions=["Ranks seeded reproducible and non-reproducible repos in the correct order"],
        uncertainties=["Auto-fix can break projects", "Scoring invites gaming"],
        evidence_status="search-incomplete", status="candidate",
        review="Good narrative, weak falsifiable claim, heavy build requirements",
        scores=dict(unmet_need=(3,2,4), differentiation=(3,2,4), time_to_value=(3,2,4),
                    build_feasibility=(3,2,4), evidence_integrity=(3,2,4),
                    distribution_leverage=(3,2,4), maintenance_burden=(3,2,4)),
    ),
    dict(
        id="I008",
        statement=(
            "A local-first AI-edit ledger that records every agent code change with its "
            "stated intent, provides intent-level blame, and supports semantic rollback "
            "of a whole agent session rather than a single diff."
        ),
        origin="ai-assisted", stage="independent", contributors=["P01", "P02"],
        assumptions=["A005"],
        predictions=["Rolls back one agent session without reverting unrelated human commits"],
        uncertainties=["Git already stores diffs", "Intent labels come from the agent and may be wrong"],
        evidence_status="search-incomplete", status="candidate",
        review="Strong timing fit but depends on a specific agent client's hook surface",
        scores=dict(unmet_need=(4,3,5), differentiation=(4,3,5), time_to_value=(3,2,4),
                    build_feasibility=(3,2,4), evidence_integrity=(4,3,5),
                    distribution_leverage=(4,3,5), maintenance_burden=(3,2,4)),
    ),
    dict(
        id="I009",
        statement=(
            "A cross-system config drift explainer that reads heterogeneous config "
            "sources and explains which single setting caused an observed behavior "
            "difference between environments."
        ),
        origin="ai-assisted", stage="independent", contributors=["P03", "P06"],
        assumptions=["A004"],
        predictions=["Attributes a seeded drift to one setting"],
        uncertainties=["Every system has a bespoke config grammar", "Causal attribution is hard"],
        evidence_status="search-incomplete", status="candidate",
        review="Broad scope, high integration cost, weak shareable artifact",
        scores=dict(unmet_need=(3,2,4), differentiation=(3,2,4), time_to_value=(2,1,3),
                    build_feasibility=(2,1,3), evidence_integrity=(3,2,4),
                    distribution_leverage=(2,1,3), maintenance_burden=(4,3,5)),
    ),
    dict(
        id="I010",
        statement=(
            "An automatic bug-report reducer that turns a GitHub issue into a minimal "
            "reproducing input using delta debugging against the reported symptom."
        ),
        origin="ai-assisted", stage="independent", contributors=["P03", "P05"],
        assumptions=["A003", "A004"],
        predictions=["Reduces a seeded failing input to a small core"],
        uncertainties=["Needs a runnable repro and an oracle", "C-Reduce-style tools exist"],
        evidence_status="challenge-located", status="candidate",
        review="Delta debugging is established; issue parsing is the thin new slice",
        scores=dict(unmet_need=(4,3,5), differentiation=(4,3,5), time_to_value=(2,1,3),
                    build_feasibility=(3,2,4), evidence_integrity=(4,3,5),
                    distribution_leverage=(3,2,4), maintenance_burden=(3,2,4)),
    ),
    dict(
        id="I011",
        statement=(
            "Post-check refinement of I001: ship the verifier as a zero-dependency CLI "
            "with a portable behavior lockfile, so a team can record behavior before a "
            "refactor and replay it afterwards, including its own architecture refactor."
        ),
        origin="mixed", stage="post-check", contributors=["P01", "P03", "P05"],
        assumptions=["A001", "A003", "A007"],
        predictions=["A lockfile recorded before a refactor replays identically afterwards"],
        uncertainties=["Lockfile format may become a maintenance surface", "Self-verification can be circular"],
        evidence_status="mixed", status="advanced-to-review",
        review="Adds the missing distribution wedge and a self-hosting proof point",
        scores=dict(unmet_need=(4,3,5), differentiation=(4,3,5), time_to_value=(5,4,5),
                    build_feasibility=(5,4,5), evidence_integrity=(4,3,5),
                    distribution_leverage=(4,3,5), maintenance_burden=(1,1,2)),
    ),
    dict(
        id="I012",
        statement=(
            "Post-check alternative: publish only an open behavior-lockfile "
            "specification and reference parsers, with no opinionated CLI."
        ),
        origin="mixed", stage="post-check", contributors=["P04", "P06"],
        assumptions=["A007"],
        predictions=["A second implementation can consume the same lockfile"],
        uncertainties=["Specs without a tool rarely attract users", "No instant first run"],
        evidence_status="search-incomplete", status="candidate",
        review="Rejected: no runnable artifact, no README-as-product moment",
        scores=dict(unmet_need=(2,1,3), differentiation=(3,2,4), time_to_value=(1,1,2),
                    build_feasibility=(4,3,5), evidence_integrity=(4,3,5),
                    distribution_leverage=(2,1,3), maintenance_burden=(2,1,3)),
    ),
]

ASSUMPTIONS = [
    ("A001", "Developers will accept writing a small explicit equivalence contract when the alternative is an untrusted refactor.", "operational", "P01", "challenged", "Run a 5-minute first-use trial and measure contract authoring time", ["novelty_landscape.md §7"]),
    ("A002", "Agent-skill and MCP interfaces will remain stable long enough for an external scanner to stay useful.", "feasibility", "P02", "challenged", "Compare two consecutive vendor manifest revisions", ["novelty_landscape.md §3"]),
    ("A003", "Generated inputs plus a bounded case budget give useful evidence without claiming proof of equivalence.", "measurement", "P03", "partially-supported", "Inject known regressions and measure detection within the case budget", ["novelty_landscape.md §2"]),
    ("A004", "A clean, reproducible execution environment can be approximated without Docker in this sandbox.", "feasibility", "P06", "untested", "Run subprocess cases in scrubbed temp directories and measure leakage", []),
    ("A005", "The dominant fear when merging AI-generated code is silent behavior change.", "value", "P05", "untested", "Survey issue and PR review language in a sample of repositories", []),
    ("A006", "A scanner that only reads static skill text cannot establish safe runtime behavior.", "mechanistic", "P02", "partially-supported", "Compare static-only scanning with runtime policy enforcement", ["novelty_landscape.md §3"]),
    ("A007", "A portable behavior lockfile is a useful artifact even without a formal equivalence proof.", "value", "P04", "untested", "Replay a lockfile against an unrelated refactor and inspect the verdict", []),
]


def build_register() -> dict:
    ideas = []
    for item in IDEAS:
        prov = {
            "contributor_ids": item["contributors"],
            "origin": item["origin"],
            "recorded_stage": item["stage"],
            "source_refs": ["novelty_landscape.md"] if item["stage"] == "post-check" else [],
            "ai_tool": "Yuanbao (session ideation)" if item["origin"] in {"ai-assisted", "mixed"} else "",
        }
        ideas.append({
            "id": item["id"],
            "statement": item["statement"],
            "provenance": prov,
            "assumption_ids": item["assumptions"],
            "predicted_observations": item["predictions"],
            "uncertainties": item["uncertainties"],
            "evidence_status": item["evidence_status"],
            "status": item["status"],
            "qualitative_review": item["review"],
        })

    assumptions = [
        {
            "id": aid, "statement": statement, "category": category,
            "owner_id": owner, "status": status,
            "test_or_check": check, "evidence_refs": refs,
        }
        for aid, statement, category, owner, status, check, refs in ASSUMPTIONS
    ]

    adversarial = [
        {
            "idea_id": "I001", "reviewer_id": "P05",
            "strongest_version": "A CI-native claim checker that produces a minimized counterexample and never claims proof",
            "disconfirming_observation": "No divergence found for a refactor a human labeled as behavior-changing",
            "alternative_explanations": ["The contract omitted the changed observable", "Input generators missed the triggering region"],
            "measurement_failure": "Volatile fields such as timestamps create false divergences",
            "sampling_failure": "Seeded cases cover only happy paths",
            "prior_evidence": "Differential runners, property-based testing and mutation testing all exist",
            "potential_harm": "A clean verdict may be read as a safety guarantee",
            "mitigation": "Explicit evidence envelope, declared normalization, UNVERIFIED status, SARIF with coverage counts",
            "residual_uncertainty": "Arbitrary equivalence is undecidable; coverage is bounded",
            "disposition": "revise",
        },
        {
            "idea_id": "I002", "reviewer_id": "P01",
            "strongest_version": "Continuous install-time and runtime policy enforcement across the skill lifecycle",
            "disconfirming_observation": "A vendor bundles an equivalent free scanner",
            "alternative_explanations": ["The detected pattern is benign", "The rule list is stale"],
            "measurement_failure": "Static text alone cannot show exfiltration",
            "sampling_failure": "Only popular skills are in the corpus",
            "prior_evidence": "Snyk Agent Scan, Cisco scanners, NVIDIA SkillSpector, mcp-scan",
            "potential_harm": "False sense of security from a clean report",
            "mitigation": "Runtime enforcement and explicit 'no findings is not proof' wording",
            "residual_uncertainty": "Vendor interfaces change faster than a rule catalog",
            "disposition": "pause",
        },
        {
            "idea_id": "I011", "reviewer_id": "P02",
            "strongest_version": "A zero-dependency CLI plus a portable lockfile that can verify the tool's own refactor",
            "disconfirming_observation": "Self-verification passes because the lockfile and the runner share the same bug",
            "alternative_explanations": ["The lockfile recorded a bug as expected behavior", "The corpus is too small"],
            "measurement_failure": "Both sides of the comparison use identical code paths",
            "sampling_failure": "Only pure functions are covered",
            "prior_evidence": "Snapshot testing has the same baseline-trust problem",
            "potential_harm": "Circular evidence presented as independent proof",
            "mitigation": "Independent golden corpus, external CLI fixtures, and an explicit circularity disclaimer",
            "residual_uncertainty": "Self-hosting is evidence, not certification",
            "disposition": "revise",
        },
    ]

    return {
        "schema_version": "1.1",
        "session": {
            "id": "still-01",
            "title": "Select one buildable open-source developer tool with a plausible 100k-star path",
            "question": (
                "Which single developer tool, buildable in one sandbox with the standard "
                "library, best combines genuine unmet usefulness, defensible "
                "differentiation, honest evidence boundaries, and a plausible path to "
                "100k+ GitHub stars?"
            ),
            "date": "2026-11-12",
            "facilitator_id": "P01",
            "decision_owner_id": "P01",
            "participant_ids": list(PARTICIPANTS),
            "represented_perspectives": list(PARTICIPANTS.values()),
            "missing_perspectives": ["Non-English-speaking developer communities", "Enterprise CI platform owners"],
            "conflicts_or_power_dynamics": [
                "The facilitator also owns the final decision; recorded as a bias risk",
                "Landscape research was read before the independent round, creating anchoring",
            ],
        },
        "scope": {
            "in_scope": ["One runnable CLI", "Standard-library only", "Honest novelty language", "CI-ready output", "Eight or more review rounds"],
            "out_of_scope": ["Funding and go-to-market execution", "Formal proof of equivalence", "Multi-language runtime instrumentation", "Guaranteeing any star count"],
            "constraints": [
                "Real: sandbox has no Docker and no outbound git access",
                "Real: only one genuine external sub-agent runtime is available",
                "Assumed: broad developer audience values refactor safety",
                "Unknown: adoption outside English-language communities",
            ],
            "prohibited_outputs": ["Claim of absolute global novelty", "Claim that 100k stars is guaranteed"],
        },
        "notices": [
            "Ideas and scores are proposals, not findings.",
            "A bounded search cannot establish that a function does not exist anywhere.",
            "Star counts measure attention, not correctness or adoption.",
        ],
        "information_governance": {
            "classification": "public",
            "contains_personal_or_sensitive_data": False,
            "contains_controlled_or_security_sensitive_data": False,
            "contains_unpublished_or_proprietary_data": False,
            "external_ai_use_permitted": "yes-for-public-landscape-research",
            "approved_record_location": "/data/workspace/brainstorm",
        },
        "assumptions": assumptions,
        "ideas": ideas,
        "clusters": [
            {"id": "C01", "relation": "shared outcome: did a change alter observable behavior", "idea_ids": ["I001", "I005", "I010", "I011", "I012"]},
            {"id": "C02", "relation": "shared mechanism: agent and skill supply-chain trust", "idea_ids": ["I002", "I006", "I008"]},
            {"id": "C03", "relation": "shared mechanism: executing documented or declared claims", "idea_ids": ["I003", "I004", "I007", "I009"]},
        ],
        "criteria": [
            {"name": name, "description": desc, "weight": weight,
             "direction": direction, "minimum": 1, "maximum": 5,
             "scale_anchors": {"1": "weak / high friction", "3": "mixed", "5": "strong / low friction"},
             "weight_set_by": "P01 before any scores were computed"}
            for name, weight, direction, desc in CRITERIA
        ],
        "literature_checks": [
            {"idea_id": "I001", "query": "differential testing property based mutation semantic diff CLI", "date": "2026-11-12", "status": "challenge-located", "note": "Adjacent techniques are mature; no equivalent integrated drop-in CLI was located"},
            {"idea_id": "I002", "query": "agent skill MCP scanner prompt injection hidden unicode", "date": "2026-11-12", "status": "challenge-located", "note": "Crowded, vendor-dependent"},
            {"idea_id": "I003", "query": "README quickstart verification container doc testing", "date": "2026-11-12", "status": "challenge-located", "note": "kibble and doc-verify occupy the workflow"},
            {"idea_id": "I010", "query": "delta debugging bug report minimal reproducing input", "date": "2026-11-12", "status": "challenge-located", "note": "C-Reduce and delta debugging established"},
        ],
        "adversarial_reviews": adversarial,
        "feasibility_and_ethics_reviews": [
            {"idea_id": "I001", "gate": "honesty", "outcome": "pass-with-conditions", "note": "Must never print 'proved equivalent'; bounded evidence envelope required"},
            {"idea_id": "I001", "gate": "safety", "outcome": "pass-with-conditions", "note": "Untrusted code runs in a subprocess with timeouts, resource limits and a scrubbed environment"},
            {"idea_id": "I002", "gate": "maintenance", "outcome": "fail", "note": "Vendor churn makes a standalone rule catalog fragile"},
            {"idea_id": "I012", "gate": "time-to-value", "outcome": "fail", "note": "A spec with no runnable CLI has no first-run moment"},
        ],
        "decision_log": [
            {
                "decision_id": "D001", "date": "2026-11-12",
                "candidate_ids": ["I001", "I002", "I003", "I005", "I008", "I011", "I012"],
                "decision": "Build I001 as revised by I011: the `still` CLI with a portable behavior lockfile",
                "rationale": (
                    "Highest disclosed score with the strongest evidence-integrity and "
                    "feasibility combination; I011 supplies the distribution wedge and a "
                    "self-hosting verification path. I002 has higher urgency but loses "
                    "the maintenance gate. I012 loses the time-to-value gate."
                ),
                "dissent": "P02 argued the security scanner has a larger immediate audience; recorded, not adopted",
                "uncertainty": "Adoption depends on contract authoring friction, which is untested",
                "revisit_trigger": "If first-use contract authoring exceeds 10 minutes in a 5-user trial, narrow the default contract surface",
                "owner_id": "P01",
                "next_action": "pilot-implementation",
            },
            {
                "decision_id": "D002", "date": "2026-11-12",
                "candidate_ids": ["I001", "I011"],
                "decision": "Reject the claim 'this function does not exist in the world already' as unverifiable",
                "rationale": "Bounded search can only support 'no equivalent integrated CLI was located'; absolute novelty is unfalsifiable",
                "dissent": "None", "uncertainty": "Unknown private or non-English prior art may exist",
                "revisit_trigger": "A reader produces a prior-art link with the same integrated workflow",
                "owner_id": "P05", "next_action": "publish-prior-art-section",
            },
            {
                "decision_id": "D003", "date": "2026-11-12",
                "candidate_ids": ["I001", "I011"],
                "decision": "Treat 105k stars as a distribution objective, never a design guarantee",
                "rationale": "Located evidence shows stars correlate with attention, timing and onboarding friction, not technical merit alone",
                "dissent": "None", "uncertainty": "No causal growth model is available",
                "revisit_trigger": "Six-month adoption and retention data become available",
                "owner_id": "P04", "next_action": "document-growth-hypothesis",
            },
        ],
        "workflow": [
            {"order": 1, "stage": "scope", "status": "complete", "method_or_deviation": None},
            {"order": 2, "stage": "independent-generation", "status": "complete", "method_or_deviation": "Anchoring deviation: landscape report was read before this round; recorded in conflicts"},
            {"order": 3, "stage": "structured-sharing", "status": "complete", "method_or_deviation": "Silent pooled sharing across six recorded perspectives"},
            {"order": 4, "stage": "structural-clustering", "status": "complete", "method_or_deviation": "Clustered by shared outcome and shared mechanism"},
            {"order": 5, "stage": "criteria-definition", "status": "complete", "method_or_deviation": "Criteria and weights fixed before computing scores"},
            {"order": 6, "stage": "adversarial-review", "status": "complete", "method_or_deviation": "Reviewers assigned to ideas they did not originate"},
            {"order": 7, "stage": "evidence-check", "status": "complete", "method_or_deviation": "Bounded public-web search; see novelty_landscape.md"},
            {"order": 8, "stage": "reopened-generation", "status": "complete", "method_or_deviation": "Produced I011 and I012, both refinements rather than new families"},
            {"order": 9, "stage": "gates-and-decision", "status": "complete", "method_or_deviation": "Honesty, safety, maintenance and time-to-value gates applied outside the additive matrix"},
        ],
        "templates": {"idea": {}, "assumption": {}},
    }


def main() -> None:
    register = build_register()
    (OUT / "session.json").write_text(json.dumps(register, indent=2) + "\n", encoding="utf-8")

    config = {
        "schema_version": "1.0",
        "criteria": [
            {"name": name, "description": desc, "weight": weight,
             "direction": direction, "minimum": 1, "maximum": 5}
            for name, weight, direction, desc in CRITERIA
        ],
    }
    (OUT / "criteria.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    names = [c[0] for c in CRITERIA]
    header = ["idea_id"]
    for name in names:
        header += [name, f"{name}_low", f"{name}_high"]
    header += ["qualitative_review", "uncertainties", "evidence_status", "ethics_status"]

    with (OUT / "scores.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for item in IDEAS:
            row = [item["id"]]
            for name in names:
                score, low, high = item["scores"][name]
                assert low <= score <= high, (item["id"], name)
                row += [score, low, high]
            row += [
                item["review"],
                "; ".join(item["uncertainties"]),
                item["evidence_status"],
                "not-applicable",
            ]
            writer.writerow(row)

    print(f"wrote session.json with {len(IDEAS)} ideas and {len(CRITERIA)} criteria")


if __name__ == "__main__":
    main()
