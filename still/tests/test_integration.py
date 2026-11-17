"""End-to-end tests: isolated execution, CLI contracts, lock and replay."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from still.cli import main, run_check, run_lock, run_replay
from still.execution import ExecutionError, run_case
from still.model import ContractError, load_contract
from still.report import DIVERGENCE, NO_DIVERGENCE, UNVERIFIED

REPO = Path(__file__).resolve().parents[1]
EXAMPLES = REPO / "examples"


def write_python(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


def contract_doc(before: str, after: str, **overrides) -> dict:
    document = {
        "schema_version": "1.0",
        "name": "integration",
        "adapter": "python",
        "before": before,
        "after": after,
        "inputs": {"seed": [1, "a"], "generators": []},
        "observe": ["return", "exception", "stdout", "stderr", "exit", "files"],
        "normalize": [],
        "allow": [],
        "budget": {"cases": 2, "timeout_ms": 1500, "seed": 3},
    }
    document.update(overrides)
    return document


def write_contract(tmp_path: Path, document: dict) -> Path:
    path = tmp_path / "case.contract.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_python_worker_returns_value_and_captures_stdout(tmp_path):
    write_python(tmp_path, "target.py", "def f(x):\n    print('hi')\n    return x * 2\n")
    contract = load_contract(write_contract(tmp_path, contract_doc("target.py::f", "target.py::f")))
    observation = run_case(contract, "before", 3)
    assert observation.return_value == 6
    assert "hi" in observation.stdout
    assert observation.exit == 0
    assert observation.files == {}
    assert observation.unverified_reason is None


def test_python_worker_records_exception_type(tmp_path):
    write_python(tmp_path, "target.py", "def f(x):\n    raise ValueError('boom')\n")
    contract = load_contract(write_contract(tmp_path, contract_doc("target.py::f", "target.py::f")))
    observation = run_case(contract, "after", 1)
    assert observation.exception is not None
    assert "ValueError" in observation.exception


def test_timeout_kills_the_child_and_marks_unverified(tmp_path):
    write_python(tmp_path, "target.py", "def f(x):\n    while True:\n        pass\n")
    doc = contract_doc("target.py::f", "target.py::f")
    doc["budget"]["timeout_ms"] = 200
    contract = load_contract(write_contract(tmp_path, doc))
    observation = run_case(contract, "before", 1)
    assert observation.timed_out is True
    assert observation.unverified_reason is not None
    assert "timeout" in observation.unverified_reason


def test_network_is_blocked_for_the_python_adapter(tmp_path):
    write_python(tmp_path, "target.py", "import socket\ndef f(x):\n    return socket.socket()\n")
    contract = load_contract(write_contract(tmp_path, contract_doc("target.py::f", "target.py::f")))
    observation = run_case(contract, "before", 1)
    assert observation.exception is not None
    assert "network access is disabled" in observation.exception


def test_target_cannot_escape_the_contract_directory(tmp_path):
    outside = tmp_path.parent / "outside_target.py"
    outside.write_text("def f(x):\n    return x\n", encoding="utf-8")
    document = contract_doc("../outside_target.py::f", "../outside_target.py::f")
    contract = load_contract(write_contract(tmp_path, document))
    with pytest.raises(ExecutionError, match="escapes"):
        run_case(contract, "before", 1)
    outside.unlink(missing_ok=True)


def test_command_adapter_runs_an_executable(tmp_path):
    body = f"#!{sys.executable}\nimport sys, json\nd = sys.stdin.read()\nprint(json.dumps({{'n': len(d)}}))\n"
    for name in ("v1", "v2"):
        path = write_python(tmp_path, f"{name}.py", body)
        path.chmod(0o755)
    doc = contract_doc("v1.py", "v2.py", adapter="command",
                       observe=["stdout", "stderr", "exit", "files"])
    contract = load_contract(write_contract(tmp_path, doc))
    observation = run_case(contract, "before", "abc")
    assert observation.exit == 0
    assert "n" in observation.stdout


def test_check_finds_the_injected_regression_with_a_counterexample():
    contract = load_contract(EXAMPLES / "parse_price.contract.json")
    contract = replace(contract, budget=replace(contract.budget, cases=20))
    result = run_check(contract)
    assert result.verdict == DIVERGENCE
    assert result.counterexample is not None
    assert result.counterexample["diffs"]
    assert result.cases_run > 0


def test_check_reports_no_divergence_for_a_clean_refactor():
    contract = load_contract(EXAMPLES / "clean.contract.json")
    contract = replace(contract, budget=replace(contract.budget, cases=10))
    result = run_check(contract)
    assert result.verdict == NO_DIVERGENCE, result.unverified


def test_lock_and_replay_agree_when_behavior_is_unchanged(tmp_path):
    contract = load_contract(EXAMPLES / "clean.contract.json")
    contract = replace(contract, budget=replace(contract.budget, cases=8))
    baseline = tmp_path / "behavior.lock.json"
    locked = run_lock(contract, str(baseline))
    assert locked.verdict == "LOCKED"
    assert baseline.is_file()
    replay = run_replay(contract, str(baseline))
    assert replay.verdict == NO_DIVERGENCE, (replay.divergences, replay.unverified)
    assert replay.envelope.get("self_verification_note")


def test_replay_detects_a_changed_implementation(tmp_path):
    contract = load_contract(EXAMPLES / "clean.contract.json")
    contract = replace(contract, budget=replace(contract.budget, cases=6))
    baseline = tmp_path / "behavior.lock.json"
    run_lock(contract, str(baseline))
    changed = replace(contract, after="modern.py::parse_price")
    replay = run_replay(changed, str(baseline))
    assert replay.verdict == DIVERGENCE


def test_lockfile_rejects_symlink_destination(tmp_path):
    contract = load_contract(EXAMPLES / "clean.contract.json")
    link = tmp_path / "link.json"
    link.symlink_to(tmp_path / "real.json")
    with pytest.raises(ContractError, match="symlink"):
        run_lock(contract, str(link))


def test_cli_check_exit_codes_and_json(capsys):
    divergence_code = main(["check", str(EXAMPLES / "parse_price.contract.json"),
                            "--cases", "12", "--format", "json", "--no-minimize"])
    assert divergence_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == DIVERGENCE
    assert payload["disclaimer"]
    equivalent_code = main(["check", str(EXAMPLES / "clean.contract.json"),
                            "--cases", "6", "--format", "json"])
    assert equivalent_code == 0


def test_cli_bad_contract_returns_error_code(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text('{"name": "x", "nope": 1}', encoding="utf-8")
    code = main(["check", str(bad)])
    assert code == 2
    assert "error:" in capsys.readouterr().err


def test_cli_unverified_when_a_case_times_out(tmp_path, capsys):
    write_python(tmp_path, "slow.py", "def f(x):\n    while True:\n        pass\n")
    doc = contract_doc("slow.py::f", "slow.py::f")
    doc["budget"]["timeout_ms"] = 150
    path = write_contract(tmp_path, doc)
    code = main(["check", str(path), "--format", "json"])
    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == UNVERIFIED
    assert payload["unverified"]


def test_init_proposes_a_contract_from_a_git_diff(tmp_path):
    env = dict(os.environ, GIT_AUTHOR_NAME="test", GIT_AUTHOR_EMAIL="t@e.st",
               GIT_COMMITTER_NAME="test", GIT_COMMITTER_EMAIL="t@e.st")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, env=env)
    target = tmp_path / "maths.py"
    target.write_text("def add(a):\n    return a\n", encoding="utf-8")
    subprocess.run(["git", "add", "maths.py"], cwd=tmp_path, check=True, env=env)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=tmp_path, check=True, env=env)
    target.write_text("def add(a):\n    return a + 0\n", encoding="utf-8")
    code = main(["init", "--repo", str(tmp_path), "--output", "proposed.json"])
    assert code == 0
    proposed = json.loads((tmp_path / "proposed.json").read_text(encoding="utf-8"))
    assert proposed["after"] == "maths.py::add"
    assert proposed["before"] == "maths.py@HEAD::add"


def test_git_materialized_target_runs(tmp_path):
    env = dict(os.environ, GIT_AUTHOR_NAME="test", GIT_AUTHOR_EMAIL="t@e.st",
               GIT_COMMITTER_NAME="test", GIT_COMMITTER_EMAIL="t@e.st")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, env=env)
    target = tmp_path / "old.py"
    target.write_text("def f(x):\n    return x\n", encoding="utf-8")
    subprocess.run(["git", "add", "old.py"], cwd=tmp_path, check=True, env=env)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=tmp_path, check=True, env=env)
    target.write_text("def f(x):\n    return x + 1\n", encoding="utf-8")
    doc = contract_doc("old.py@HEAD::f", "old.py::f")
    contract = load_contract(write_contract(tmp_path, doc))
    result = run_check(contract)
    assert result.verdict == DIVERGENCE


def test_unverified_verdict_has_exit_code_two():
    from still.report import CheckResult, exit_code
    assert exit_code(CheckResult(name="x", verdict=UNVERIFIED)) == 2
