"""Adversarial inputs and malformed artifacts found in review round 5."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from still.cli import _apply_overrides
from still.equivalence import compare
from still.execution import resolve_target
from still.inputs import canonical_json
from still.lockfile import read_lock
from still.model import ContractError, parse_contract

BASE = {
    "schema_version": "1.0",
    "name": "robust",
    "adapter": "python",
    "before": "a.py::f",
    "after": "b.py::f",
    "inputs": {"seed": [], "generators": []},
    "observe": ["return", "exception"],
    "normalize": [],
    "allow": [],
    "budget": {"cases": 10, "timeout_ms": 1000, "seed": 1},
}


def contract(**overrides):
    return parse_contract({**BASE, **overrides}, Path("."))


@pytest.mark.parametrize("bad", [
    [["return"]], [{"x": 1}], [None], [3.5], ["return", ["return"]],
])
def test_observe_rejects_non_string_fields(bad):
    with pytest.raises(ContractError, match="unknown field"):
        contract(observe=bad)


@pytest.mark.parametrize("bad_ref", ["--upload-pack=evil", "HEAD;rm", "a:b", "-x", ""])
def test_unsafe_git_refs_are_rejected(tmp_path, bad_ref):
    c = contract(before=f"a.py@{bad_ref}::f")
    with pytest.raises(ContractError, match="unsafe git ref"):
        resolve_target(c, c.before, tmp_path)


def test_float_tolerance_is_reported_when_it_fires():
    c = contract(normalize=[{"kind": "float_tolerance", "field": "return", "abs_tol": 0.1, "rel_tol": 0}])
    equal, _, applied = compare({"return": 1.0, "exception": None}, {"return": 1.05, "exception": None}, c)
    assert equal
    assert applied == ["float_tolerance(return)"]


def test_cli_override_cannot_exceed_the_case_cap():
    args = argparse.Namespace(cases=10**9, seed=None, timeout_ms=None)
    with pytest.raises(ContractError, match="--cases"):
        _apply_overrides(contract(), args)


def test_cli_override_cannot_disable_the_timeout():
    args = argparse.Namespace(cases=None, seed=None, timeout_ms=0)
    with pytest.raises(ContractError, match="--timeout-ms"):
        _apply_overrides(contract(), args)


def test_cli_override_accepts_a_valid_value():
    args = argparse.Namespace(cases=25, seed=8, timeout_ms=900)
    changed = _apply_overrides(contract(), args)
    assert (changed.budget.cases, changed.budget.seed, changed.budget.timeout_ms) == (25, 8, 900)


def test_lockfile_rejects_a_non_object_signature(tmp_path):
    path = tmp_path / "bad.lock.json"
    path.write_text(json.dumps({
        "schema_version": "1.0",
        "contract_digest": "a" * 64,
        "cases": [1],
        "signatures": [["not", "a", "dict"]],
        "envelope": {},
    }), encoding="utf-8")
    with pytest.raises(ContractError, match=r"signatures\[0\]"):
        read_lock(path)


def test_lockfile_rejects_mismatched_lengths(tmp_path):
    path = tmp_path / "bad.lock.json"
    path.write_text(json.dumps({
        "schema_version": "1.0",
        "contract_digest": "a" * 64,
        "cases": [1, 2],
        "signatures": [{"return": 1}],
        "envelope": {},
    }), encoding="utf-8")
    with pytest.raises(ContractError, match="non-empty and equal"):
        read_lock(path)


def test_canonical_json_handles_non_string_keys_in_nested_values():
    assert canonical_json({"a": [1, {"b": 2}]}) == '{"a":[1,{"b":2}]}'


def test_contract_rejects_a_non_object_budget():
    with pytest.raises(ContractError, match="budget"):
        contract(budget=[1, 2, 3])


def test_contract_rejects_a_symlink_read_through_for_lockfiles(tmp_path):
    real = tmp_path / "real.json"
    real.write_text("{}", encoding="utf-8")
    link = tmp_path / "link.json"
    link.symlink_to(real)
    with pytest.raises(ContractError, match="symlink"):
        read_lock(link)
