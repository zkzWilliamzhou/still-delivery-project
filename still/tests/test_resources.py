"""Round 7: timeouts, output caps, file caps, process groups and env scrubbing."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from still.execution import run_case
from still.model import ContractError


def make(tmp_path: Path, body: str, *, timeout_ms: int = 400, observe=None) -> tuple[Path, object]:
    target = tmp_path / "target.py"
    target.write_text(body, encoding="utf-8")
    document = {
        "schema_version": "1.0",
        "name": "resources",
        "adapter": "python",
        "before": "target.py::f",
        "after": "target.py::f",
        "inputs": {"seed": [1], "generators": []},
        "observe": observe or ["return", "exception", "stdout", "stderr", "exit", "files"],
        "normalize": [],
        "allow": [],
        "budget": {"cases": 1, "timeout_ms": timeout_ms, "seed": 1},
    }
    path = tmp_path / "c.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    from still.model import load_contract
    return target, load_contract(path)


def test_timeout_marks_the_case_unverified(tmp_path):
    _, contract = make(tmp_path, "def f(x):\n    while True:\n        pass\n")
    obs = run_case(contract, "before", 1)
    assert obs.timed_out is True
    assert obs.unverified_reason and "timeout" in obs.unverified_reason
    assert obs.exit != 0


def test_child_process_group_is_killed_on_timeout(tmp_path):
    marker = "STILL_LEAK_MARKER_73491"
    body = (
        "import subprocess, sys, time\n"
        "def f(x):\n"
        f"    subprocess.Popen([sys.executable, '-c', "
        f"'import time; time.sleep(30)  # {marker}'])\n"
        "    time.sleep(30)\n"
        "    return 1\n"
    )
    _, contract = make(tmp_path, body, timeout_ms=500)
    obs = run_case(contract, "before", 1)
    assert obs.timed_out is True
    leaked: list[str] = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cmdline = (entry / "cmdline").read_bytes().decode("utf-8", "replace")
        except OSError:
            continue
        if marker in cmdline and str(entry.name) != str(os.getpid()):
            leaked.append(entry.name)
    assert not leaked, f"child processes survived the group kill: {leaked}"


def test_large_stdout_is_capped_and_unverified(tmp_path):
    body = (
        "def f(x):\n"
        "    import sys\n"
        "    sys.stdout.write('A' * 2_000_000)\n"
        "    return 1\n"
    )
    _, contract = make(tmp_path, body, timeout_ms=3000)
    obs = run_case(contract, "before", 1)
    assert len(obs.stdout) <= 1_000_000
    assert obs.unverified_reason and "capture cap" in obs.unverified_reason


def test_many_files_are_capped_and_unverified(tmp_path):
    body = (
        "def f(x):\n"
        "    for i in range(200):\n"
        "        with open('f' + str(i), 'w') as handle:\n"
        "            handle.write('x')\n"
        "    return 1\n"
    )
    _, contract = make(tmp_path, body, timeout_ms=3000)
    obs = run_case(contract, "before", 1)
    assert obs.files.get("__truncated__") is True
    assert obs.unverified_reason and "files" in obs.unverified_reason


def test_target_cannot_read_inherited_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv("STILL_TEST_SECRET", "do-not-leak")
    body = (
        "import os\n"
        "def f(x):\n"
        "    return os.environ.get('STILL_TEST_SECRET', 'absent')\n"
    )
    _, contract = make(tmp_path, body)
    obs = run_case(contract, "before", 1)
    assert obs.return_value == "absent"


def test_python_worker_disables_sockets(tmp_path):
    body = (
        "import socket\n"
        "def f(x):\n"
        "    return socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
    )
    _, contract = make(tmp_path, body)
    obs = run_case(contract, "before", 1)
    assert obs.exception and "network access is disabled" in obs.exception


def test_command_target_must_be_executable(tmp_path):
    script = tmp_path / "cmd.py"
    script.write_text("print('hi')\n", encoding="utf-8")
    document = {
        "schema_version": "1.0", "name": "cmd", "adapter": "command",
        "before": "cmd.py", "after": "cmd.py",
        "inputs": {"seed": [1], "generators": []},
        "observe": ["stdout", "stderr", "exit", "files"],
        "normalize": [], "allow": [],
        "budget": {"cases": 1, "timeout_ms": 1000, "seed": 1},
    }
    path = tmp_path / "c.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    from still.model import load_contract
    from still.execution import ExecutionError
    contract = load_contract(path)
    try:
        run_case(contract, "before", 1)
    except ExecutionError as exc:
        assert "not executable" in str(exc)
    else:
        raise AssertionError("expected ExecutionError for a non-executable command target")


def test_contract_file_size_is_bounded(tmp_path):
    huge = tmp_path / "huge.json"
    huge.write_text(" " * 1_100_000, encoding="utf-8")
    from still.model import load_contract
    try:
        load_contract(huge)
    except ContractError as exc:
        assert "too large" in str(exc)
    else:
        raise AssertionError("expected ContractError for an oversized contract")


def test_worker_module_runs_under_the_active_interpreter():
    # Guard against a shebang assumption in tests on minimal images.
    assert sys.executable
