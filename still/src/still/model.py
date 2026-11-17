"""Contract model, strict validation and shared value objects."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"
MAX_CONTRACT_BYTES = 1_000_000
MAX_CASES = 100_000
MAX_TIMEOUT_MS = 120_000
MAX_STRING_LEN = 4096
MAX_SEED_CASES = 10_000
MAX_GENERATORS = 32

OBSERVABLES = ("return", "exception", "stdout", "stderr", "exit", "files")
ADAPTERS = ("python", "command")
GENERATOR_KINDS = ("strings", "ints", "floats", "enum", "cases")
NORMALIZE_KINDS = (
    "strip",
    "sort_lines",
    "lower",
    "regex_replace",
    "ignore_field",
    "float_tolerance",
)

DEFAULT_OBSERVE = {
    "python": ("return", "exception", "stdout", "stderr", "exit", "files"),
    "command": ("stdout", "stderr", "exit", "files"),
}

_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")


class StillError(Exception):
    """Base error for the still package."""


class ContractError(StillError):
    """A contract is malformed or violates a safety bound."""


class ExecutionError(StillError):
    """A case could not be executed in a comparable way."""


def canonical_json(value: Any) -> str:
    """Return a deterministic JSON representation used for dedupe and hashing."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def digest(value: Any) -> str:
    """Return a stable sha256 digest of a JSON-serializable value."""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Budget:
    cases: int = 240
    timeout_ms: int = 2000
    seed: int = 1337


@dataclass(frozen=True)
class Contract:
    name: str
    adapter: str
    before: str
    after: str
    inputs: dict[str, Any]
    observe: tuple[str, ...]
    normalize: list[dict[str, Any]]
    allow: list[str]
    budget: Budget
    base_dir: Path
    allow_outside: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize the contract without machine-local paths."""
        return {
            "schema_version": SCHEMA_VERSION,
            "name": self.name,
            "adapter": self.adapter,
            "before": self.before,
            "after": self.after,
            "inputs": self.inputs,
            "observe": list(self.observe),
            "normalize": self.normalize,
            "allow": self.allow,
            "budget": {
                "cases": self.budget.cases,
                "timeout_ms": self.budget.timeout_ms,
                "seed": self.budget.seed,
            },
        }

    def digest(self) -> str:
        """Stable identity of the declared claim, used by lockfiles."""
        return digest(self.to_dict())


def _require_keys(obj: dict[str, Any], allowed: set[str], where: str) -> None:
    unknown = sorted(set(obj) - allowed)
    if unknown:
        raise ContractError(f"{where}: unknown keys {unknown}")


def _bounded_int(value: Any, low: int, high: int, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"{where}: expected an integer")
    if not low <= value <= high:
        raise ContractError(f"{where}: expected {low}..{high}, got {value}")
    return value


def _bounded_number(value: Any, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{where}: expected a number")
    result = float(value)
    if result != result or result in (float("inf"), float("-inf")):
        raise ContractError(f"{where}: expected a finite number")
    if abs(result) > 1e15:
        raise ContractError(f"{where}: magnitude too large")
    return result


def _validate_generator(spec: Any, index: int) -> dict[str, Any]:
    where = f"inputs.generators[{index}]"
    if not isinstance(spec, dict):
        raise ContractError(f"{where}: expected an object")
    kind = spec.get("kind")
    if kind not in GENERATOR_KINDS:
        raise ContractError(f"{where}.kind: expected one of {list(GENERATOR_KINDS)}")
    _bounded_int(spec.get("count", 50), 0, MAX_CASES, f"{where}.count")

    if kind == "strings":
        alphabet = spec.get("alphabet", "abc012 ")
        if not isinstance(alphabet, str) or not alphabet or len(alphabet) > 256:
            raise ContractError(f"{where}.alphabet: expected a string of 1..256 chars")
        min_len = _bounded_int(spec.get("min_len", 0), 0, MAX_STRING_LEN, f"{where}.min_len")
        max_len = _bounded_int(spec.get("max_len", 12), 0, MAX_STRING_LEN, f"{where}.max_len")
        if min_len > max_len:
            raise ContractError(f"{where}: min_len exceeds max_len")
        _require_keys(spec, {"kind", "count", "alphabet", "min_len", "max_len"}, where)
        return spec
    if kind in ("ints", "floats"):
        low = _bounded_number(spec.get("min", -100), f"{where}.min")
        high = _bounded_number(spec.get("max", 100), f"{where}.max")
        if low > high:
            raise ContractError(f"{where}: min exceeds max")
        _require_keys(spec, {"kind", "count", "min", "max"}, where)
        return spec
    if kind in ("enum", "cases"):
        values = spec.get("values")
        if not isinstance(values, list) or not values:
            raise ContractError(f"{where}.values: expected a non-empty list")
        if len(values) > MAX_SEED_CASES:
            raise ContractError(f"{where}.values: too many values")
        for item in values:
            if len(canonical_json(item)) > MAX_STRING_LEN:
                raise ContractError(f"{where}.values: value too large")
        _require_keys(spec, {"kind", "count", "values"}, where)
        return spec
    raise ContractError(f"{where}: unsupported generator")


def _validate_normalizer(rule: Any, index: int, observe: tuple[str, ...]) -> dict[str, Any]:
    where = f"normalize[{index}]"
    if not isinstance(rule, dict):
        raise ContractError(f"{where}: expected an object")
    kind = rule.get("kind")
    if kind not in NORMALIZE_KINDS:
        raise ContractError(f"{where}.kind: expected one of {list(NORMALIZE_KINDS)}")
    field = rule.get("field", "")
    if field not in observe:
        raise ContractError(f"{where}.field: must be one of the observed fields {list(observe)}")
    if kind == "regex_replace":
        pattern = rule.get("pattern")
        if not isinstance(pattern, str) or len(pattern) > 512:
            raise ContractError(f"{where}.pattern: expected a short regex")
        try:
            re.compile(pattern)
        except re.error as exc:
            raise ContractError(f"{where}.pattern: invalid regex: {exc}") from exc
        replacement = rule.get("replacement", "")
        if not isinstance(replacement, str) or len(replacement) > 512:
            raise ContractError(f"{where}.replacement: expected a short string")
        _require_keys(rule, {"kind", "field", "pattern", "replacement"}, where)
    elif kind == "float_tolerance":
        abs_tol = _bounded_number(rule.get("abs_tol", 1e-9), f"{where}.abs_tol")
        rel_tol = _bounded_number(rule.get("rel_tol", 0.0), f"{where}.rel_tol")
        if abs_tol < 0 or rel_tol < 0:
            raise ContractError(f"{where}: tolerances must be non-negative")
        _require_keys(rule, {"kind", "field", "abs_tol", "rel_tol"}, where)
    else:
        _require_keys(rule, {"kind", "field"}, where)
    return rule


def parse_contract(data: Any, base_dir: Path, *, allow_outside: bool = False) -> Contract:
    """Validate an in-memory contract document."""
    if not isinstance(data, dict):
        raise ContractError("contract: expected a JSON object")
    allowed = {
        "schema_version", "name", "adapter", "before", "after", "inputs",
        "observe", "normalize", "allow", "budget",
    }
    _require_keys(data, allowed, "contract")

    name = data.get("name")
    if not isinstance(name, str) or not _NAME_RE.match(name):
        raise ContractError("name: expected 1..80 chars of [A-Za-z0-9_.-]")
    adapter = data.get("adapter", "python")
    if adapter not in ADAPTERS:
        raise ContractError(f"adapter: expected one of {list(ADAPTERS)}")
    for side in ("before", "after"):
        target = data.get(side)
        if not isinstance(target, str) or not target.strip() or len(target) > 1024:
            raise ContractError(f"{side}: expected a non-empty target string")

    inputs = data.get("inputs", {"seed": [], "generators": []})
    if not isinstance(inputs, dict):
        raise ContractError("inputs: expected an object")
    _require_keys(inputs, {"seed", "generators"}, "inputs")
    seed = inputs.get("seed", [])
    if not isinstance(seed, list) or len(seed) > MAX_SEED_CASES:
        raise ContractError(f"inputs.seed: expected a list of at most {MAX_SEED_CASES} cases")
    for item in seed:
        if len(canonical_json(item)) > MAX_STRING_LEN:
            raise ContractError("inputs.seed: case too large")
    generators = inputs.get("generators", [])
    if not isinstance(generators, list) or len(generators) > MAX_GENERATORS:
        raise ContractError(f"inputs.generators: expected at most {MAX_GENERATORS} generators")
    checked_generators = [_validate_generator(g, i) for i, g in enumerate(generators)]

    observe_raw = data.get("observe")
    if observe_raw is None:
        observe = DEFAULT_OBSERVE[adapter]
    else:
        if not isinstance(observe_raw, list) or not observe_raw:
            raise ContractError("observe: expected a non-empty list")
        observe = tuple(observe_raw)
    for field in observe:
        if field not in OBSERVABLES:
            raise ContractError(f"observe: unknown field {field!r}; expected {list(OBSERVABLES)}")
    if len(set(observe)) != len(observe):
        raise ContractError("observe: duplicate fields")
    if adapter == "command" and "return" in observe:
        raise ContractError(
            "observe: 'return' is not available for the command adapter; observe stdout instead"
        )
    if adapter == "command" and "exception" in observe:
        raise ContractError("observe: 'exception' is not available for the command adapter")

    normalize_raw = data.get("normalize", [])
    if not isinstance(normalize_raw, list) or len(normalize_raw) > 32:
        raise ContractError("normalize: expected at most 32 rules")
    normalize = [_validate_normalizer(r, i, observe) for i, r in enumerate(normalize_raw)]

    allow = data.get("allow", [])
    if not isinstance(allow, list) or any(not isinstance(f, str) or f not in OBSERVABLES for f in allow):
        raise ContractError(f"allow: expected field names from {list(OBSERVABLES)}")

    budget_raw = data.get("budget", {})
    if not isinstance(budget_raw, dict):
        raise ContractError("budget: expected an object")
    _require_keys(budget_raw, {"cases", "timeout_ms", "seed"}, "budget")
    budget = Budget(
        cases=_bounded_int(budget_raw.get("cases", 240), 1, MAX_CASES, "budget.cases"),
        timeout_ms=_bounded_int(budget_raw.get("timeout_ms", 2000), 1, MAX_TIMEOUT_MS, "budget.timeout_ms"),
        seed=_bounded_int(budget_raw.get("seed", 1337), -(2**31), 2**31 - 1, "budget.seed"),
    )

    version = data.get("schema_version", SCHEMA_VERSION)
    if version != SCHEMA_VERSION:
        raise ContractError(f"schema_version: expected {SCHEMA_VERSION!r}")

    return Contract(
        name=name, adapter=adapter, before=data["before"], after=data["after"],
        inputs={"seed": seed, "generators": checked_generators},
        observe=observe, normalize=normalize, allow=allow, budget=budget,
        base_dir=base_dir.resolve(), allow_outside=allow_outside,
    )


def load_contract(path: str | Path, *, allow_outside: bool = False) -> Contract:
    """Load and validate a contract file with a bounded size."""
    contract_path = Path(path).resolve()
    if not contract_path.is_file():
        raise ContractError(f"contract file not found: {contract_path}")
    size = contract_path.stat().st_size
    if size > MAX_CONTRACT_BYTES:
        raise ContractError(f"contract file too large: {size} bytes (limit {MAX_CONTRACT_BYTES})")
    try:
        data = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"contract file could not be read: {exc}") from exc
    return parse_contract(data, contract_path.parent, allow_outside=allow_outside)
