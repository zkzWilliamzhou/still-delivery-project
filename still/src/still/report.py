"""Machine-readable and human reports with a visible evidence boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .equivalence import dump_json
from .inputs import case_label
from .model import SCHEMA_VERSION

NO_DIVERGENCE = "NO_DIVERGENCE_FOUND"
DIVERGENCE = "DIVERGENCE"
UNVERIFIED = "UNVERIFIED"
LOCKED = "LOCKED"

DISCLAIMER = (
    "This is bounded evidence over the stated cases, not a proof of equivalence. "
    "Untried inputs, unobserved effects and non-determinism remain outside the claim."
)


@dataclass
class CheckResult:
    name: str
    verdict: str
    cases_run: int = 0
    divergences: list[dict[str, Any]] = field(default_factory=list)
    counterexample: dict[str, Any] | None = None
    unverified: list[str] = field(default_factory=list)
    envelope: dict[str, Any] = field(default_factory=dict)
    normalizers: list[str] = field(default_factory=list)
    allowed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "name": self.name,
            "verdict": self.verdict,
            "cases_run": self.cases_run,
            "divergences": self.divergences,
            "counterexample": self.counterexample,
            "unverified": self.unverified,
            "envelope": self.envelope,
            "normalizers_applied": self.normalizers,
            "allowed_divergences": self.allowed,
            "disclaimer": DISCLAIMER,
        }


def exit_code(result: CheckResult) -> int:
    if result.verdict in (NO_DIVERGENCE, LOCKED):
        return 0
    if result.verdict == DIVERGENCE:
        return 1
    return 2


def _text(result: CheckResult) -> str:
    lines = [
        f"{result.verdict}  {result.name}  "
        f"{len(result.divergences)} of {result.cases_run} cases diverged"
    ]
    if result.counterexample:
        item = result.counterexample
        lines.append(f"  counterexample: {case_label(item['case'])}")
        for diff in item.get("diffs", []):
            lines.append(f"    {diff}")
        lines.append(
            f"  minimized in {item.get('reductions', 0)} reductions "
            f"({item.get('evaluations', 0)} re-runs)"
        )
    if result.unverified:
        lines.append("  unverified:")
        for reason in result.unverified[:10]:
            lines.append(f"    - {reason}")
        if len(result.unverified) > 10:
            lines.append(f"    - ... {len(result.unverified) - 10} more")
    env = result.envelope
    lines.append(
        "Evidence envelope: "
        f"{result.cases_run} cases, seed {env.get('seed')}, "
        f"generators=[{', '.join(env.get('generators', []))}], "
        f"observed=[{', '.join(env.get('observe', []))}], "
        f"normalizers=[{', '.join(result.normalizers) or 'none'}], "
        f"allowed=[{', '.join(result.allowed) or 'none'}], "
        f"timeout={env.get('timeout_ms')}ms."
    )
    lines.append(DISCLAIMER)
    return "\n".join(lines) + "\n"


def _sarif(result: CheckResult) -> str:
    results: list[dict[str, Any]] = []
    for item in result.divergences:
        results.append({
            "ruleId": "STILL001",
            "level": "error",
            "message": {"text": "; ".join(item.get("diffs", []))[:1000]},
            "properties": {"case": case_label(item.get("case")), "still:name": result.name},
        })
    for reason in result.unverified:
        results.append({
            "ruleId": "STILL002",
            "level": "warning",
            "message": {"text": reason[:1000]},
        })
    if not results:
        results.append({
            "ruleId": "STILL000",
            "level": "note",
            "message": {"text": f"No divergence found in {result.cases_run} bounded cases. {DISCLAIMER}"},
        })
    document = {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [{
            "tool": {"driver": {
                "name": "still", "version": "0.1.0", "informationUri": "https://github.com/",
                "rules": [
                    {"id": "STILL000", "name": "Bounded equivalence evidence"},
                    {"id": "STILL001", "name": "Behavior divergence"},
                    {"id": "STILL002", "name": "Unverified case"},
                ],
            }},
            "properties": {"still:envelope": result.envelope, "still:disclaimer": DISCLAIMER},
            "results": results,
        }],
    }
    return dump_json(document) + "\n"


def _markdown(result: CheckResult) -> str:
    env = result.envelope
    lines = [
        f"# Behavior certificate: {result.name}",
        "",
        f"**Verdict:** `{result.verdict}`",
        "",
        f"Cases run: {result.cases_run}. Seed: {env.get('seed')}. "
        f"Adapter: {env.get('adapter')}. Timeout: {env.get('timeout_ms')} ms.",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Observed | {', '.join(env.get('observe', []))} |",
        f"| Generators | {', '.join(env.get('generators', [])) or 'seed only'} |",
        f"| Normalizers applied | {', '.join(result.normalizers) or 'none'} |",
        f"| Allowed divergences | {', '.join(result.allowed) or 'none'} |",
        "",
    ]
    if result.counterexample:
        item = result.counterexample
        lines += [
            "## Minimal counterexample",
            "",
            "```json",
            dump_json(item.get("case")),
            "```",
            "",
            *[f"- {diff}" for diff in item.get("diffs", [])],
            "",
        ]
    if result.unverified:
        lines += ["## Unverified", "", *[f"- {reason}" for reason in result.unverified], ""]
    lines += ["## Boundary", "", DISCLAIMER, ""]
    return "\n".join(lines)


def render(result: CheckResult, fmt: str) -> str:
    if fmt == "json":
        return dump_json(result.to_dict()) + "\n"
    if fmt == "sarif":
        return _sarif(result)
    if fmt == "markdown":
        return _markdown(result)
    if fmt == "text":
        return _text(result)
    raise ValueError(f"unknown format: {fmt}")


__all__ = [
    "DISCLAIMER",
    "DIVERGENCE",
    "LOCKED",
    "NO_DIVERGENCE",
    "UNVERIFIED",
    "CheckResult",
    "exit_code",
    "render",
]
