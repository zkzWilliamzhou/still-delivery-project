"""Isolated execution of one case against one implementation.

Each side runs in a fresh subprocess with a scrubbed environment, a private
working directory, CPU and address-space limits, an output file cap, and a
process-group kill on timeout. This reduces risk; it is not a security sandbox
for hostile code. The README says to use a container for that.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import signal
# Required for isolated target execution; every call uses argv and shell=False.
import subprocess  # nosec B404
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .gitbin import git_binary
from .model import Contract, ContractError, ExecutionError, canonical_json

MAX_OUTPUT_BYTES = 1_000_000
MAX_FILE_BYTES = 1_000_000
MAX_FILES = 64
MEM_BYTES = 512 * 1024 * 1024
_REF_RE = re.compile(r"^[A-Za-z0-9_./^~-]{1,128}$")


@dataclass(frozen=True)
class Observation:
    return_value: Any
    exception: str | None
    stdout: str
    stderr: str
    exit: int
    files: dict[str, Any]
    timed_out: bool
    duration_ms: int
    unverified_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "return": self.return_value,
            "exception": self.exception,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit": self.exit,
            "files": self.files,
            "timed_out": self.timed_out,
            "duration_ms": self.duration_ms,
            "unverified_reason": self.unverified_reason,
        }

def _apply_limits(cpu_seconds: int) -> None:
    """Best-effort resource limits applied inside the child before exec."""
    if os.name != "posix":
        return
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
        resource.setrlimit(resource.RLIMIT_AS, (MEM_BYTES, MEM_BYTES))
        resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT_BYTES, MAX_OUTPUT_BYTES))
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    except (ImportError, OSError, ValueError):
        # A platform that refuses a limit still gets the parent-side timeout.
        return


def _scrubbed_env(contract: Contract, side: str, work: Path) -> dict[str, str]:
    package_parent = str(Path(__file__).resolve().parent.parent)
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "HOME": str(work),
        "TMPDIR": str(work),
        "PYTHONPATH": package_parent,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "STILL_SIDE": side,
        "STILL_CONTRACT": contract.name,
    }


def _contained(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except (ValueError, OSError):
        return False


def _git_show(contract: Contract, rel: str, ref: str) -> bytes:
    if not _REF_RE.match(ref) or ref.startswith("-"):
        raise ContractError(f"unsafe git ref: {ref!r}")
    try:
        # B603: argv is a fixed list, shell=False, ref is regex-validated and
        # rel is confined to the contract directory. No user string becomes a shell word.
        completed = subprocess.run(  # nosec B603
            [git_binary(), "show", f"{ref}:{rel}"],
            cwd=str(contract.base_dir), capture_output=True, timeout=10,
            check=False, shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ContractError(f"git show failed for {ref}:{rel}: {exc}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", "replace").strip()[:200]
        raise ContractError(f"git show failed for {ref}:{rel}: {detail}")
    return completed.stdout


def resolve_target(contract: Contract, target: str, cache_dir: Path) -> tuple[Path, str]:
    """Resolve a target spec into (path, function_name).

    Python targets use ``path.py::func`` or ``path.py@REF::func``.
    Command targets use ``path`` or ``path@REF`` and must be executable.
    """
    if "::" in target:
        if contract.adapter != "python":
            raise ContractError("command adapter targets must not contain '::'")
        path_spec, function = target.rsplit("::", 1)
        if not function.isidentifier():
            raise ContractError(f"invalid function name: {function!r}")
    else:
        if contract.adapter != "command":
            raise ContractError("python adapter targets need 'path.py::func'")
        path_spec, function = target, ""

    ref: str | None = None
    if "@" in path_spec:
        path_spec, ref = path_spec.rsplit("@", 1)
        if not _REF_RE.match(ref) or ref.startswith("-"):
            raise ContractError(f"unsafe git ref: {ref!r}")
    raw = Path(path_spec)
    candidate = raw.resolve() if raw.is_absolute() else (contract.base_dir / raw).resolve()
    if not contract.allow_outside and not _contained(candidate, contract.base_dir):
        raise ContractError(f"target escapes the contract directory: {path_spec}")

    rel = os.path.relpath(str(candidate), str(contract.base_dir)).replace(os.sep, "/")
    if rel.startswith(".."):
        raise ContractError(f"target escapes the contract directory: {path_spec}")

    if ref is not None:
        content = _git_show(contract, rel, ref)
        if len(content) > 2_000_000:
            raise ContractError(f"git object too large: {ref}:{rel}")
        suffix = ".py" if contract.adapter == "python" else ".bin"
        out = cache_dir / f"target_{abs(hash((rel, ref))) % 10_000_000}{suffix}"
        out.write_bytes(content)
        if suffix == ".bin":
            out.chmod(0o700)
        return out, function

    if not candidate.is_file():
        raise ContractError(f"target file not found: {path_spec}")
    return candidate, function


def _snapshot_files(work: Path) -> tuple[dict[str, Any], str | None]:
    entries: dict[str, Any] = {}
    total = 0
    count = 0
    try:
        paths = sorted(work.rglob("*"), key=lambda p: str(p))
    except OSError as exc:
        return {}, f"working directory could not be scanned: {exc}"
    for path in paths:
        if not path.is_file() or path.is_symlink():
            continue
        count += 1
        if count > MAX_FILES:
            return {"__truncated__": True}, f"more than {MAX_FILES} files written"
        try:
            size = path.stat().st_size
        except OSError:
            continue
        total += size
        if total > MAX_FILE_BYTES:
            return {"__truncated__": True}, "files exceeded the byte cap"
        rel = str(path.relative_to(work)).replace(os.sep, "/")
        entries[rel] = {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "size": size,
        }
    return entries, None


def _read_capped(path: Path) -> str:
    try:
        with path.open("rb") as handle:
            raw = handle.read(MAX_OUTPUT_BYTES + 1)
    except OSError:
        return ""
    if len(raw) > MAX_OUTPUT_BYTES:
        raw = raw[:MAX_OUTPUT_BYTES]
    return raw.decode("utf-8", "replace")


def run_case(contract: Contract, side: str, case: Any) -> Observation:
    """Execute one case against one side and capture declared observables."""
    target = contract.before if side == "before" else contract.after
    started = time.monotonic()
    timeout_s = max(0.05, contract.budget.timeout_ms / 1000.0)
    cpu_seconds = max(1, math.ceil(timeout_s) + 1)

    with tempfile.TemporaryDirectory(prefix="still-case-") as root:
        root_path = Path(root)
        work = root_path / "work"
        ctrl = root_path / "ctrl"
        work.mkdir()
        ctrl.mkdir()
        try:
            resolved, function = resolve_target(contract, target, ctrl)
        except ContractError as exc:
            raise ExecutionError(str(exc)) from exc

        stdout_path = ctrl / "stdout"
        stderr_path = ctrl / "stderr"
        stdin_path = ctrl / "stdin"
        result_path = ctrl / "result.json"
        request_path = ctrl / "request.json"
        stdin_path.write_text(canonical_json(case), encoding="utf-8")

        env = _scrubbed_env(contract, side, work)
        if contract.adapter == "python":
            request_path.write_text(json.dumps({
                "module": str(resolved),
                "function": function,
                "case": case,
                "result_path": str(result_path),
            }, ensure_ascii=False, default=str), encoding="utf-8")
            command = [sys.executable, "-m", "still._worker", str(request_path)]
        else:
            if not os.access(str(resolved), os.X_OK):
                raise ExecutionError(f"command target is not executable: {target}")
            command = [str(resolved)]

        timed_out = False
        exit_code = -1
        with stdin_path.open("rb") as stdin_handle, \
                stdout_path.open("wb") as stdout_handle, \
                stderr_path.open("wb") as stderr_handle:
            # B603: argv is built from a validated absolute path, shell=False,
            # stdin is a file, and the child gets scrubbed env plus rlimits.
            proc = subprocess.Popen(  # nosec B603
                command, cwd=str(work), env=env, stdin=stdin_handle,
                stdout=stdout_handle, stderr=stderr_handle,
                start_new_session=True, shell=False,
                preexec_fn=(lambda: _apply_limits(cpu_seconds)) if os.name == "posix" else None,
            )
            try:
                exit_code = proc.wait(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                timed_out = True
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError, OSError):
                    proc.kill()
                try:
                    exit_code = proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    exit_code = -1

        stdout = _read_capped(stdout_path)
        stderr = _read_capped(stderr_path)
        return_value: Any = None
        exception: str | None = None
        if contract.adapter == "python" and result_path.is_file():
            try:
                payload = json.loads(result_path.read_text(encoding="utf-8"))
                return_value = payload.get("return")
                exception = payload.get("exception")
            except (OSError, UnicodeError, json.JSONDecodeError):
                exception = "StillError: worker result was unreadable"
        elif contract.adapter == "python":
            exception = "StillError: worker produced no result"

        files, file_reason = _snapshot_files(work)
        reasons: list[str] = []
        if timed_out:
            reasons.append(f"timeout after {contract.budget.timeout_ms}ms")
        if file_reason:
            reasons.append(file_reason)
        if len(stdout) >= MAX_OUTPUT_BYTES or len(stderr) >= MAX_OUTPUT_BYTES:
            reasons.append("output reached the capture cap")
        if contract.adapter == "command":
            # The command adapter has no in-child network guard. Say so.
            pass

        duration_ms = int((time.monotonic() - started) * 1000)
        return Observation(
            return_value=return_value, exception=exception,
            stdout=stdout, stderr=stderr, exit=exit_code, files=files,
            timed_out=timed_out, duration_ms=duration_ms,
            unverified_reason="; ".join(reasons) if reasons else None,
        )


def observation_signature(observation: Observation, contract: Contract) -> dict[str, Any]:
    """Return only the fields the contract declares as observable."""
    source = observation.to_dict()
    return {field: source.get(field) for field in contract.observe}
