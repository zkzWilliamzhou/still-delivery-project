"""Prove the architecture pass changed no program function.

Record mode runs before the refactor and stores deterministic report hashes plus
behavior lockfiles. Verify mode replays those lockfiles with --strict and
re-runs every check, then compares the hashes byte for byte.

    PYTHONPATH=src python3 scripts/verify_function_preservation.py record
    PYTHONPATH=src python3 scripts/verify_function_preservation.py verify
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / ".golden"
ENV = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
EXAMPLES = ROOT / "examples"

CHECKS = [
    ("clean", ["check", "examples/clean.contract.json", "--cases", "10", "--format", "json"]),
    ("parse_price", ["check", "examples/parse_price.contract.json", "--cases", "20", "--format", "json"]),
    ("parse_price_no_minimize", ["check", "examples/parse_price.contract.json", "--cases", "20",
                                  "--format", "json", "--no-minimize"]),
    ("command", ["check", "examples/command.contract.json", "--cases", "10", "--format", "json"]),
    ("self", ["check", "examples/self.contract.json", "--cases", "8", "--format", "json"]),
    ("clean_sarif", ["check", "examples/clean.contract.json", "--cases", "8", "--format", "sarif"]),
    ("clean_markdown", ["check", "examples/clean.contract.json", "--cases", "8", "--format", "markdown"]),
]

LOCKS = [
    ("clean", "examples/clean.contract.json", "8"),
    ("self", "examples/self.contract.json", "8"),
]


def run(*args: str) -> tuple[int, str, str]:
    completed = subprocess.run(
        [sys.executable, "-m", "still", *args],
        cwd=str(ROOT), env=ENV, capture_output=True, text=True, timeout=180,
    )
    return completed.returncode, completed.stdout, completed.stderr


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def record() -> int:
    GOLDEN.mkdir(exist_ok=True)
    manifest: dict[str, object] = {"checks": {}, "locks": {}}
    for name, args in CHECKS:
        code, out, err = run(*args)
        if code not in (0, 1, 2):
            print(f"FAIL record {name}: exit {code}: {err[:200]}")
            return 1
        manifest["checks"][name] = {"exit": code, "sha256": digest(out), "bytes": len(out)}
        print(f"recorded check {name:26s} exit={code} sha256={digest(out)[:12]}")
    for name, contract, cases in LOCKS:
        destination = GOLDEN / f"{name}.lock.json"
        code, _, err = run("lock", contract, "--cases", cases, "--output", str(destination))
        if code != 0 or not destination.is_file():
            print(f"FAIL record lock {name}: exit {code}: {err[:200]}")
            return 1
        payload = destination.read_text(encoding="utf-8")
        manifest["locks"][name] = {"sha256": digest(payload), "bytes": len(payload)}
        print(f"recorded lock  {name:26s} sha256={digest(payload)[:12]}")
    (GOLDEN / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"\nRecorded {len(CHECKS)} checks and {len(LOCKS)} lockfiles in {GOLDEN}")
    return 0


def verify() -> int:
    manifest_path = GOLDEN / "manifest.json"
    if not manifest_path.is_file():
        print("FAIL: no .golden/manifest.json. Run record mode before the refactor.")
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []

    for name, args in CHECKS:
        expected = manifest["checks"][name]
        code, out, err = run(*args)
        actual_hash = digest(out)
        if code != expected["exit"] or actual_hash != expected["sha256"]:
            failures.append(
                f"{name}: exit {code} (expected {expected['exit']}), sha256 {actual_hash[:12]} "
                f"(expected {expected['sha256'][:12]})"
            )
            print(f"FAIL check {name}")
        else:
            print(f"PASS check {name:26s} identical report")

    for name, contract, cases in LOCKS:
        baseline = GOLDEN / f"{name}.lock.json"
        payload = baseline.read_text(encoding="utf-8")
        if digest(payload) != manifest["locks"][name]["sha256"]:
            failures.append(f"{name}: baseline lockfile changed on disk")
            print(f"FAIL lock  {name} baseline mutated")
            continue
        code, out, err = run("replay", contract, "--baseline", str(baseline),
                             "--cases", cases, "--strict", "--format", "json")
        if code != 0:
            failures.append(f"{name}: replay exit {code}: {out[:200]} {err[:200]}")
            print(f"FAIL replay {name} exit={code}")
        else:
            print(f"PASS replay {name:26s} no divergence")

    if failures:
        print("\nFUNCTION PRESERVATION FAILED:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(f"\nAll {len(CHECKS)} reports identical and {len(LOCKS)} lockfile replays clean.")
    print("No observable function changed during the architecture pass.")
    return 0


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "verify"
    if mode not in ("record", "verify"):
        print("usage: verify_function_preservation.py record|verify")
        raise SystemExit(2)
    raise SystemExit(record() if mode == "record" else verify())
