"""Declared normalization, equivalence comparison and delta debugging.

Normalization is never implicit. Every rule that fires appears in the report.
A clean verdict means "no divergence found within the stated envelope".
"""

from __future__ import annotations

import copy
import json
import math
import re
from typing import Any
from collections.abc import Callable

from .model import Contract, canonical_json

Predicate = Callable[[Any], bool]


def _short(value: Any, limit: int = 180) -> str:
    text = canonical_json(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def normalize(signature: dict[str, Any], rules: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    """Apply declared rules and return the rules that actually fired."""
    result = copy.deepcopy(signature)
    applied: list[str] = []
    for rule in rules:
        kind = rule["kind"]
        field = rule["field"]
        label = f"{kind}({field})"
        if kind == "float_tolerance":
            # Comparison applies this rule to numeric values under `field`.
            # Report it so a clean verdict cannot hide a widened comparison.
            if field in result:
                applied.append(label)
            continue
        if kind == "ignore_field":
            if field in result:
                result.pop(field)
                applied.append(label)
            continue
        if field not in result or not isinstance(result[field], str):
            continue
        value = result[field]
        if kind == "strip":
            result[field] = value.strip()
        elif kind == "lower":
            result[field] = value.lower()
        elif kind == "sort_lines":
            result[field] = "\n".join(sorted(value.splitlines()))
        elif kind == "regex_replace":
            result[field] = re.sub(rule["pattern"], rule["replacement"], value)
        applied.append(label)
    return result, applied


def _tolerance(rules: list[dict[str, Any]], field: str) -> tuple[float, float] | None:
    for rule in rules:
        if rule["kind"] == "float_tolerance" and rule["field"] == field:
            return float(rule.get("abs_tol", 1e-9)), float(rule.get("rel_tol", 0.0))
    return None


def _equal(left: Any, right: Any, tol: tuple[float, float] | None) -> bool:
    if tol and isinstance(left, (int, float)) and isinstance(right, (int, float)) \
            and not isinstance(left, bool) and not isinstance(right, bool):
        abs_tol, rel_tol = tol
        return math.isclose(float(left), float(right), abs_tol=abs_tol, rel_tol=rel_tol)
    if isinstance(left, dict) and isinstance(right, dict):
        if set(left) != set(right):
            return False
        return all(_equal(left[k], right[k], tol) for k in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(_equal(a, b, tol) for a, b in zip(left, right, strict=False))
    return canonical_json(left) == canonical_json(right)


def compare(
    before: dict[str, Any], after: dict[str, Any], contract: Contract
) -> tuple[bool, list[str], list[str]]:
    """Return (equivalent, differences, normalizers_that_fired)."""
    norm_before, applied_before = normalize(before, contract.normalize)
    norm_after, _ = normalize(after, contract.normalize)
    differences: list[str] = []
    for field in contract.observe:
        if field in contract.allow:
            continue
        if field not in norm_before and field not in norm_after:
            continue
        if not _equal(norm_before.get(field), norm_after.get(field), _tolerance(contract.normalize, field)):
            differences.append(
                f"{field}: before={_short(norm_before.get(field))} after={_short(norm_after.get(field))}"
            )
    return not differences, differences, applied_before


def _candidates(case: Any, granularity: int) -> list[Any]:
    if isinstance(case, str):
        if len(case) < 2:
            return []
        size = max(1, len(case) // granularity)
        return [
            case[:i] + case[i + size:]
            for i in range(0, len(case), size)
            if len(case[:i] + case[i + size:]) < len(case)
        ]
    if isinstance(case, list):
        if len(case) < 2:
            return []
        size = max(1, len(case) // granularity)
        return [case[:i] + case[i + size:] for i in range(0, len(case), size)]
    if isinstance(case, dict):
        return [{k: v for k, v in case.items() if k != key} for key in case]
    return []


def minimize(case: Any, predicate: Predicate, max_evals: int = 200) -> tuple[Any, int]:
    """Shrink a divergent case while the divergence still holds.

    Works character-wise for strings, element-wise for lists, and key-wise for
    dictionaries. Returns the smallest case found and the evaluation count.
    """
    evaluations = 0
    current = case
    granularity = 2

    def holds(candidate: Any) -> bool:
        nonlocal evaluations
        if evaluations >= max_evals:
            return False
        evaluations += 1
        try:
            return predicate(candidate)
        except Exception:
            return False

    while evaluations < max_evals:
        options = _candidates(current, granularity)
        if not options:
            break
        reduced = False
        for candidate in options:
            if holds(candidate):
                current = candidate
                granularity = max(2, granularity - 1)
                reduced = True
                break
        if not reduced:
            if isinstance(current, (str, list)) and granularity >= len(current):
                break
            if isinstance(current, dict) and granularity >= len(current) + 1:
                break
            granularity = min(
                len(current) if isinstance(current, (str, list)) else len(current) + 1,
                granularity * 2,
            )
    return current, evaluations


def dump_json(value: Any) -> str:
    """Pretty JSON used by lockfiles and reports."""
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, default=str)
