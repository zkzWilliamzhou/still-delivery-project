"""Deterministic, bounded case generation for differential checks."""

from __future__ import annotations

import random
from typing import Any

from .model import Contract, canonical_json


def _generate(spec: dict[str, Any], rng: random.Random) -> list[Any]:
    kind = spec["kind"]
    count = spec.get("count", 50)
    if kind == "strings":
        alphabet = spec.get("alphabet", "abc012 ")
        min_len = spec.get("min_len", 0)
        max_len = spec.get("max_len", 12)
        return [
            "".join(rng.choice(alphabet) for _ in range(rng.randint(min_len, max_len)))
            for _ in range(count)
        ]
    if kind == "ints":
        low, high = int(spec.get("min", -100)), int(spec.get("max", 100))
        return [rng.randint(low, high) for _ in range(count)]
    if kind == "floats":
        low_f, high_f = float(spec.get("min", -100)), float(spec.get("max", 100))
        return [low_f + (high_f - low_f) * rng.random() for _ in range(count)]
    if kind in ("enum", "cases"):
        values = spec["values"]
        if kind == "cases":
            return [values[i % len(values)] for i in range(min(count, len(values)))]
        return [values[rng.randrange(len(values))] for _ in range(count)]
    raise AssertionError(f"unhandled generator kind: {kind}")


def build_cases(contract: Contract) -> list[Any]:
    """Return a stable, deduplicated, bounded list of cases."""
    # B311: random.Random is chosen deliberately for reproducible test inputs.
    # It is never used for secrets, tokens or any security decision.
    rng = random.Random(contract.budget.seed)  # nosec
    cases: list[Any] = list(contract.inputs.get("seed", []))
    for spec in contract.inputs.get("generators", []):
        cases.extend(_generate(spec, rng))

    seen: set[str] = set()
    unique: list[Any] = []
    for case in cases:
        key = canonical_json(case)
        if key in seen:
            continue
        seen.add(key)
        unique.append(case)
        if len(unique) >= contract.budget.cases:
            break
    return unique


def case_label(case: Any, limit: int = 120) -> str:
    """Short, single-line rendering of a case for reports."""
    text = canonical_json(case)
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text
