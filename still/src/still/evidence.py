"""The claim module: what a verdict covers and how a verdict is classified.

This module concentrates the semantics that three orchestration loops used to
reconstruct for themselves. Its interface is narrow: ``build_envelope`` and
``classify``. Deleting it would push the evidence envelope and the verdict rule
back into three separate loops, duplicating the same logic.

It deliberately does not import ``execution``. That keeps the seam clean: this
module knows about contracts, cases and verdicts, not about subprocesses.
"""

from __future__ import annotations

from typing import Any

from .model import Contract
from .report import DIVERGENCE, NO_DIVERGENCE, UNVERIFIED

MAX_REPORTED_DIVERGENCES = 1000


def build_envelope(contract: Contract, cases: list[Any]) -> dict[str, Any]:
    """Describe exactly what a verdict covers."""
    return {
        "adapter": contract.adapter,
        "cases_requested": contract.budget.cases,
        "cases_run": len(cases),
        "seed": contract.budget.seed,
        "timeout_ms": contract.budget.timeout_ms,
        "generators": [g["kind"] for g in contract.inputs.get("generators", [])],
        "observe": list(contract.observe),
        "normalizers_declared": [r["kind"] for r in contract.normalize],
        "allow": list(contract.allow),
        "isolation": "subprocess, scrubbed env, private temp cwd, rlimits, process-group kill",
    }


def classify(divergences: list[dict[str, Any]], unverified: list[str]) -> str:
    """Classify a run. A divergence wins; unverified never becomes a pass."""
    if divergences:
        return DIVERGENCE
    if unverified:
        return UNVERIFIED
    return NO_DIVERGENCE


__all__ = ["MAX_REPORTED_DIVERGENCES", "build_envelope", "classify"]
