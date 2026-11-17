"""The claim module's narrow interface is the test surface.

These tests cross the same seam as the three CLI adapter loops: no subprocesses,
no fixtures on disk beyond a contract document.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from still.evidence import MAX_REPORTED_DIVERGENCES, build_envelope, classify
from still.model import parse_contract
from still.report import DIVERGENCE, NO_DIVERGENCE, UNVERIFIED

BASE = {
    "schema_version": "1.0",
    "name": "claim",
    "adapter": "python",
    "before": "a.py::f",
    "after": "b.py::f",
    "inputs": {"seed": [1], "generators": [{"kind": "ints", "min": 0, "max": 3, "count": 4}]},
    "observe": ["return", "exception"],
    "normalize": [],
    "allow": [],
    "budget": {"cases": 7, "timeout_ms": 900, "seed": 13},
}


def contract(**overrides):
    return parse_contract({**BASE, **overrides}, Path("."))


def test_envelope_states_the_boundary_exactly():
    env = build_envelope(contract(), [1, 2, 3])
    assert env == {
        "adapter": "python",
        "cases_requested": 7,
        "cases_run": 3,
        "seed": 13,
        "timeout_ms": 900,
        "generators": ["ints"],
        "observe": ["return", "exception"],
        "normalizers_declared": [],
        "allow": [],
        "isolation": "subprocess, scrubbed env, private temp cwd, rlimits, process-group kill",
    }


def test_envelope_reflects_declared_normalizers_and_allowances():
    c = contract(
        normalize=[{"kind": "strip", "field": "stdout"}],
        allow=["stderr"],
        observe=["return", "exception", "stdout", "stderr", "exit", "files"],
    )
    env = build_envelope(c, [])
    assert env["normalizers_declared"] == ["strip"]
    assert env["allow"] == ["stderr"]
    assert env["cases_run"] == 0


@pytest.mark.parametrize("divergences,unverified,expected", [
    ([], [], NO_DIVERGENCE),
    ([{"case": 1}], [], DIVERGENCE),
    ([], ["case 2: timeout"], UNVERIFIED),
    ([{"case": 1}], ["case 2: timeout"], DIVERGENCE),
])
def test_classify_never_turns_an_unverified_run_into_a_pass(divergences, unverified, expected):
    assert classify(divergences, unverified) == expected


def test_divergence_cap_is_a_single_constant():
    assert MAX_REPORTED_DIVERGENCES == 1000


def test_deletion_test_holds_for_the_claim_module():
    """If the module vanished, both envelope and verdict rules would need owners."""
    c = contract()
    env = build_envelope(c, [1])
    assert env["cases_requested"] == c.budget.cases
    assert classify([], []) == NO_DIVERGENCE
    # The two decisions live behind one importable interface, not in a CLI loop.
    assert callable(build_envelope) and callable(classify)
