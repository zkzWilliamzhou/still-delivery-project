"""Unit tests for contracts, generators, equivalence and reports."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from still.equivalence import compare, minimize, normalize
from still.inputs import build_cases, case_label
from still.model import ContractError, canonical_json, parse_contract
from still.report import (
    DIVERGENCE, NO_DIVERGENCE, UNVERIFIED, CheckResult, exit_code, render,
)


def make_contract(tmp_path: Path, **overrides):
    document = {
        "schema_version": "1.0",
        "name": "demo",
        "adapter": "python",
        "before": "a.py::f",
        "after": "b.py::f",
        "inputs": {"seed": [1, 2], "generators": []},
        "observe": ["return", "exception"],
        "normalize": [],
        "allow": [],
        "budget": {"cases": 10, "timeout_ms": 1000, "seed": 42},
    }
    document.update(overrides)
    return parse_contract(document, tmp_path)


def test_canonical_json_is_key_order_independent():
    assert canonical_json({"b": 2, "a": 1}) == canonical_json({"a": 1, "b": 2})


def test_default_observe_depends_on_adapter(tmp_path):
    doc = {"name": "x", "adapter": "command", "before": "a", "after": "b", "inputs": {"seed": []}}
    contract = parse_contract(doc, tmp_path)
    assert "return" not in contract.observe
    assert "stdout" in contract.observe


def test_unknown_contract_key_is_rejected(tmp_path):
    with pytest.raises(ContractError, match="unknown keys"):
        make_contract(tmp_path, surprise=True)


def test_bad_adapter_is_rejected(tmp_path):
    with pytest.raises(ContractError, match="adapter"):
        make_contract(tmp_path, adapter="ruby")


def test_command_adapter_cannot_observe_return(tmp_path):
    with pytest.raises(ContractError, match="command adapter"):
        make_contract(tmp_path, adapter="command", before="a", after="b", observe=["return"])


def test_unknown_observable_is_rejected(tmp_path):
    with pytest.raises(ContractError, match="unknown field"):
        make_contract(tmp_path, observe=["return", "vibes"])


def test_case_budget_is_bounded(tmp_path):
    with pytest.raises(ContractError, match=r"budget\.cases"):
        make_contract(tmp_path, budget={"cases": 10**9, "timeout_ms": 1000, "seed": 1})


def test_invalid_normalizer_regex_is_rejected(tmp_path):
    rules = [{"kind": "regex_replace", "field": "return", "pattern": "([", "replacement": ""}]
    with pytest.raises(ContractError, match="invalid regex"):
        make_contract(tmp_path, normalize=rules)


def test_normalizer_field_must_be_observed(tmp_path):
    with pytest.raises(ContractError, match="observed fields"):
        make_contract(tmp_path, normalize=[{"kind": "strip", "field": "stdout"}])


def test_generators_are_deterministic(tmp_path):
    contract = make_contract(tmp_path, inputs={
        "seed": [],
        "generators": [{"kind": "strings", "alphabet": "ab", "min_len": 1, "max_len": 6, "count": 30}],
    })
    assert build_cases(contract) == build_cases(contract)


def test_cases_are_deduplicated(tmp_path):
    contract = make_contract(
        tmp_path,
        inputs={"seed": [1, 1, 2, 2], "generators": [{"kind": "ints", "min": 1, "max": 3, "count": 50}]},
        budget={"cases": 5, "timeout_ms": 1000, "seed": 9},
    )
    cases = build_cases(contract)
    assert len(cases) == 3
    assert len({canonical_json(c) for c in cases}) == 3


def test_case_budget_caps_a_wide_generator(tmp_path):
    contract = make_contract(
        tmp_path,
        inputs={
            "seed": [],
            "generators": [
                {"kind": "strings", "alphabet": "abcdef", "min_len": 4, "max_len": 6, "count": 200}
            ],
        },
        budget={"cases": 7, "timeout_ms": 1000, "seed": 9},
    )
    cases = build_cases(contract)
    assert len(cases) == 7
    assert len({canonical_json(c) for c in cases}) == 7


def test_case_label_truncates():
    assert case_label("x" * 500, limit=20).endswith("...")


def test_compare_detects_a_difference(tmp_path):
    contract = make_contract(tmp_path)
    equal, diffs, _ = compare({"return": 1, "exception": None}, {"return": 2, "exception": None}, contract)
    assert not equal
    assert any(diff.startswith("return:") for diff in diffs)


def test_compare_ignores_unobserved_fields(tmp_path):
    contract = make_contract(tmp_path)
    equal, _, _ = compare(
        {"return": 1, "exception": None, "stdout": "a"},
        {"return": 1, "exception": None, "stdout": "b"},
        contract,
    )
    assert equal


def test_allow_list_is_recorded_and_skips_the_field(tmp_path):
    contract = make_contract(tmp_path, allow=["exception"])
    equal, diffs, _ = compare({"return": 1, "exception": "A"}, {"return": 1, "exception": "B"}, contract)
    assert equal and not diffs


def test_float_tolerance_is_explicit(tmp_path):
    contract = make_contract(tmp_path, normalize=[
        {"kind": "float_tolerance", "field": "return", "abs_tol": 0.01, "rel_tol": 0.0}
    ])
    equal, _, _ = compare({"return": 1.0, "exception": None}, {"return": 1.005, "exception": None}, contract)
    assert equal
    strict = replace(contract, normalize=[])
    not_equal, _, _ = compare(
        {"return": 1.0, "exception": None},
        {"return": 1.005, "exception": None},
        strict,
    )
    assert not not_equal


def test_normalize_reports_rules_that_fired(tmp_path):
    contract = make_contract(tmp_path, observe=["return", "stdout"], normalize=[
        {"kind": "strip", "field": "stdout"},
        {"kind": "sort_lines", "field": "stdout"},
    ])
    normalized, applied = normalize({"stdout": "  b\na  ", "return": 1}, contract.normalize)
    assert normalized["stdout"] == "a\nb"
    assert len(applied) == 2


def test_ignore_field_removes_it_from_both_sides(tmp_path):
    contract = make_contract(tmp_path, normalize=[{"kind": "ignore_field", "field": "exception"}])
    equal, _, applied = compare({"return": 1, "exception": "a"}, {"return": 1, "exception": "b"}, contract)
    assert equal and applied == ["ignore_field(exception)"]


def test_minimize_shrinks_a_string():
    def still_diverges(candidate):
        return "x" in candidate

    small, evals = minimize("abcxabc", still_diverges)
    assert "x" in small and len(small) < len("abcxabc")
    assert evals > 0


def test_minimize_shrinks_a_dict():
    def still_diverges(candidate):
        return candidate.get("bad") == 1

    small, _ = minimize({"good": 1, "bad": 1, "extra": 2}, still_diverges)
    assert small == {"bad": 1}


def test_minimize_is_bounded():
    calls = []

    def always_true(candidate):
        calls.append(candidate)
        return True

    minimize("a" * 200, always_true, max_evals=5)
    assert len(calls) <= 5


def test_report_formats_carry_the_disclaimer():
    result = CheckResult(
        name="demo", verdict=NO_DIVERGENCE, cases_run=3,
        envelope={"seed": 1, "timeout_ms": 1000, "observe": ["return"], "generators": []},
    )
    for fmt in ("text", "json", "sarif", "markdown"):
        text = render(result, fmt)
        assert "not a proof" in text.lower() or "disclaimer" in text.lower()
        assert len(text) > 20


def test_sarif_contains_a_result_for_a_divergence():
    result = CheckResult(
        name="demo", verdict=DIVERGENCE, cases_run=1,
        divergences=[{"case": "x", "diffs": ["return: before=1 after=2"]}],
        envelope={"seed": 1},
    )
    payload = json.loads(render(result, "sarif"))
    assert payload["version"] == "2.1.0"
    assert payload["runs"][0]["results"][0]["ruleId"] == "STILL001"


def test_exit_codes():
    assert exit_code(CheckResult(name="a", verdict=NO_DIVERGENCE)) == 0
    assert exit_code(CheckResult(name="a", verdict=DIVERGENCE)) == 1
    assert exit_code(CheckResult(name="a", verdict=UNVERIFIED)) == 2
