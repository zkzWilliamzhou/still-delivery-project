"""Round 6 evidence: exercise every CLI command, format and exit code.

Run from the repository root:
    PYTHONPATH=src python3 scripts/cli_matrix.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
EXAMPLES = ROOT / "examples"


def run(*args: str) -> tuple[int, str, str]:
    completed = subprocess.run(
        [sys.executable, "-m", "still", *args],
        cwd=str(ROOT), env=ENV, capture_output=True, text=True, timeout=120,
    )
    return completed.returncode, completed.stdout, completed.stderr


def check(label: str, condition: bool, detail: str = "") -> bool:
    status = "PASS" if condition else "FAIL"
    print(f"{status:4s}  {label}" + (f"  [{detail}]" if detail and not condition else ""))
    return condition


def main() -> int:
    results: list[bool] = []

    code, _, _ = run("--version")
    results.append(check("--version exits 0", code == 0, f"code={code}"))

    code, out, _ = run("check", str(EXAMPLES / "clean.contract.json"), "--cases", "6")
    results.append(check("clean refactor exits 0", code == 0, f"code={code}"))
    results.append(check("clean refactor says NO_DIVERGENCE_FOUND", "NO_DIVERGENCE_FOUND" in out))

    code, out, _ = run("check", str(EXAMPLES / "parse_price.contract.json"),
                       "--cases", "20", "--no-minimize")
    results.append(check("divergence exits 1", code == 1, f"code={code}"))
    results.append(check("divergence says DIVERGENCE", "DIVERGENCE" in out))

    code, out, _ = run("check", str(EXAMPLES / "parse_price.contract.json"), "--cases", "20")
    results.append(check("minimized counterexample is printed", "counterexample:" in out))

    for fmt in ("json", "sarif", "markdown"):
        code, out, _ = run("check", str(EXAMPLES / "clean.contract.json"),
                           "--cases", "6", "--format", fmt)
        parsed_ok = False
        if fmt == "json":
            parsed_ok = json.loads(out)["verdict"] == "NO_DIVERGENCE_FOUND"
        elif fmt == "sarif":
            parsed_ok = json.loads(out)["version"] == "2.1.0"
        else:
            parsed_ok = out.startswith("# Behavior certificate")
        results.append(check(f"format {fmt} is well formed", code == 0 and parsed_ok))

    with tempfile.TemporaryDirectory() as tmp:
        lock = str(Path(tmp) / "behavior.lock.json")
        code, _, err = run("lock", str(EXAMPLES / "clean.contract.json"),
                           "--cases", "8", "--output", lock)
        results.append(check("lock exits 0", code == 0, f"code={code} err={err[:120]}"))
        results.append(check("lock writes a lockfile", Path(lock).is_file()))

        code, out, _ = run("replay", str(EXAMPLES / "clean.contract.json"),
                           "--baseline", lock, "--cases", "8", "--strict")
        results.append(check("replay against unchanged behavior exits 0", code == 0, f"code={code}"))
        results.append(check("replay reports NO_DIVERGENCE_FOUND", "NO_DIVERGENCE_FOUND" in out))

        cert = str(Path(tmp) / "cert.md")
        code, _, _ = run("check", str(EXAMPLES / "clean.contract.json"),
                         "--cases", "6", "--format", "markdown", "--output", cert)
        results.append(check("--output writes the report to a file", Path(cert).is_file()))

    # A malformed contract must fail cleanly with exit 2, not a traceback.
    with tempfile.TemporaryDirectory() as tmp:
        bad = Path(tmp) / "bad.json"
        bad.write_text('{"name": "x", "unknown": 1}', encoding="utf-8")
        code, _, err = run("check", str(bad))
        results.append(check("malformed contract exits 2", code == 2, f"code={code}"))
        results.append(check("malformed contract has no traceback", "Traceback" not in err))

    code, _, err = run("check", str(EXAMPLES / "clean.contract.json"), "--cases", str(10**9))
    results.append(check("out-of-range --cases is rejected", code == 2 and "--cases" in err,
                         f"code={code} err={err[:120]}"))

    print(f"\n{sum(results)}/{len(results)} CLI contract checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
