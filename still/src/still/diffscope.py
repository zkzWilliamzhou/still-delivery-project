"""Propose a contract from the changed functions in a git diff."""

from __future__ import annotations

import re
# Fixed argv git inspection only; no shell, no user-controlled command words.
import subprocess  # nosec B404
from pathlib import Path

from .equivalence import dump_json
from .gitbin import git_binary
from .model import ContractError

_DEF_RE = re.compile(r"^def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.MULTILINE)


def changed_python_files(repo_dir: Path) -> list[str]:
    """Return python paths from the working-tree diff, plus untracked ones."""
    try:
        git = git_binary()
        # B603: fixed argv, shell=False, output is parsed as paths and confined below.
        completed = subprocess.run(  # nosec B603
            [git, "diff", "--name-only", "--diff-filter=ACMR", "--", "*.py"],
            cwd=str(repo_dir), capture_output=True, text=True, timeout=10,
            check=False, shell=False,
        )
        untracked = subprocess.run(  # nosec B603
            [git, "ls-files", "--others", "--exclude-standard", "--", "*.py"],
            cwd=str(repo_dir), capture_output=True, text=True, timeout=10,
            check=False, shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ContractError(f"git inspection failed: {exc}") from exc
    paths = set(completed.stdout.splitlines()) | set(untracked.stdout.splitlines())
    root = repo_dir.resolve()
    safe: list[str] = []
    for rel in paths:
        rel = rel.strip()
        if not rel or "\x00" in rel:
            continue
        candidate = Path(rel)
        if candidate.is_absolute() or ".." in candidate.parts:
            continue
        try:
            (root / candidate).resolve().relative_to(root)
        except (ValueError, OSError):
            continue
        safe.append(rel)
    return sorted(safe)


def propose_contract(repo_dir: Path, ref: str = "HEAD") -> dict:
    """Return a starter contract for the first changed top-level function."""
    paths = changed_python_files(repo_dir)
    if not paths:
        raise ContractError("init: no changed python files found in the working tree")
    for rel in paths:
        candidate = repo_dir / rel
        if not candidate.is_file():
            continue
        text = candidate.read_text(encoding="utf-8", errors="replace")
        names = _DEF_RE.findall(text)
        if not names:
            continue
        function = names[0]
        return {
            "schema_version": "1.0",
            "name": f"{Path(rel).stem}-{function}",
            "adapter": "python",
            "before": f"{rel}@{ref}::{function}",
            "after": f"{rel}::{function}",
            "inputs": {
                "seed": ["", 0, 1, -1, "abc"],
                "generators": [
                    {"kind": "strings", "alphabet": "abc012 $.-", "min_len": 0, "max_len": 12, "count": 80},
                    {"kind": "ints", "min": -100, "max": 100, "count": 40},
                ],
            },
            "observe": ["return", "exception", "stdout", "stderr", "exit", "files"],
            "normalize": [],
            "allow": [],
            "budget": {"cases": 120, "timeout_ms": 2000, "seed": 1337},
        }
    raise ContractError("init: changed python files contain no top-level functions")


def write_proposed_contract(repo_dir: Path, ref: str, output: str | None) -> Path:
    """Write the proposed contract and return its path."""
    document = propose_contract(repo_dir, ref)
    name = output or f"{document['name']}.contract.json"
    destination = (repo_dir / name).resolve()
    try:
        destination.relative_to(repo_dir.resolve())
    except ValueError as exc:
        raise ContractError("init: output path escapes the repository") from exc
    if destination.is_symlink():
        raise ContractError("init: refusing to write through a symlink")
    destination.write_text(dump_json(document) + "\n", encoding="utf-8")
    return destination
