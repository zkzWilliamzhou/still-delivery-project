"""Command line entry point for still."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any
from collections.abc import Sequence

from .diffscope import write_proposed_contract
from .equivalence import compare, minimize
from .evidence import MAX_REPORTED_DIVERGENCES, build_envelope, classify
from .execution import ExecutionError, observation_signature, run_case
from .inputs import build_cases, case_label
from .lockfile import lock_matches_contract, read_lock, write_lock
from .model import (
    MAX_CASES, MAX_TIMEOUT_MS, Contract, ContractError, StillError, load_contract,
)
from .report import LOCKED, CheckResult, exit_code, render

FORMATS = ("text", "json", "sarif", "markdown")
MINIMIZE_EVALS = 60


def _pair(contract: Contract, case: Any) -> tuple[Any, Any]:
    before = run_case(contract, "before", case)
    after = run_case(contract, "after", case)
    return before, after


def run_check(contract: Contract, *, do_minimize: bool = True) -> CheckResult:
    """Run before and after over the generated corpus."""
    cases = build_cases(contract)
    divergences: list[dict[str, Any]] = []
    unverified: list[str] = []
    applied: list[str] = []
    attempted = 0

    for case in cases:
        attempted += 1
        label = case_label(case)
        try:
            before, after = _pair(contract, case)
        except ExecutionError as exc:
            unverified.append(f"{label}: {exc}")
            continue
        if before.unverified_reason:
            unverified.append(f"{label}: before: {before.unverified_reason}")
        if after.unverified_reason:
            unverified.append(f"{label}: after: {after.unverified_reason}")
        before_sig = observation_signature(before, contract)
        after_sig = observation_signature(after, contract)
        equivalent, diffs, fired = compare(before_sig, after_sig, contract)
        for name in fired:
            if name not in applied:
                applied.append(name)
        if not equivalent:
            divergences.append({"case": case, "diffs": diffs, "before": before_sig, "after": after_sig})
            if len(divergences) > MAX_REPORTED_DIVERGENCES:
                break

    if len(divergences) > MAX_REPORTED_DIVERGENCES:
        unverified.append("divergence list truncated at the reporting cap")

    counterexample: dict[str, Any] | None = None
    if divergences and do_minimize:
        original = divergences[0]["case"]

        def still_diverges(candidate: Any) -> bool:
            try:
                before, after = _pair(contract, candidate)
            except ExecutionError:
                return False
            equivalent, _, _ = compare(
                observation_signature(before, contract),
                observation_signature(after, contract),
                contract,
            )
            return not equivalent

        minimized, evaluations = minimize(original, still_diverges, max_evals=MINIMIZE_EVALS)
        try:
            before, after = _pair(contract, minimized)
            _, final_diffs, _ = compare(
                observation_signature(before, contract),
                observation_signature(after, contract),
                contract,
            )
        except ExecutionError:
            final_diffs = ["counterexample could not be re-run after minimization"]
        counterexample = {
            "case": minimized,
            "original": original,
            "diffs": final_diffs,
            "evaluations": evaluations,
            "reductions": max(0, len(case_label(original)) - len(case_label(minimized))),
        }

    env = build_envelope(contract, cases)
    env["cases_attempted"] = attempted
    return CheckResult(
        name=contract.name, verdict=classify(divergences, unverified),
        cases_run=attempted, divergences=divergences, counterexample=counterexample,
        unverified=unverified, envelope=env,
        normalizers=applied, allowed=list(contract.allow),
    )


def run_lock(contract: Contract, output: str) -> CheckResult:
    """Record the before implementation's behavior as a portable lockfile."""
    cases = build_cases(contract)
    signatures: list[dict[str, Any]] = []
    unverified: list[str] = []
    for case in cases:
        label = case_label(case)
        try:
            observation = run_case(contract, "before", case)
        except ExecutionError as exc:
            unverified.append(f"{label}: {exc}")
            signatures.append({})
            continue
        if observation.unverified_reason:
            unverified.append(f"{label}: {observation.unverified_reason}")
        signatures.append(observation_signature(observation, contract))
    payload = write_lock(output, contract, cases, signatures, build_envelope(contract, cases))
    if any(not item for item in signatures):
        unverified.append("some cases produced no signature; replay cannot verify them")
    result = CheckResult(
        name=contract.name, verdict=LOCKED, cases_run=len(cases),
        unverified=unverified, envelope=payload["envelope"],
    )
    return result


def run_replay(contract: Contract, baseline: str, *, strict: bool = False) -> CheckResult:
    """Replay the after implementation against a recorded lockfile."""
    payload = read_lock(baseline)
    cases = payload["cases"]
    signatures = payload["signatures"]
    divergences: list[dict[str, Any]] = []
    unverified: list[str] = []
    applied: list[str] = []
    if not lock_matches_contract(payload, contract):
        message = "contract digest differs from the lockfile; the declared claim changed"
        if strict:
            raise ContractError(message)
        unverified.append(message)
    for case, expected in zip(cases, signatures, strict=False):
        if not expected:
            continue
        label = case_label(case)
        try:
            observation = run_case(contract, "after", case)
        except ExecutionError as exc:
            unverified.append(f"{label}: {exc}")
            continue
        if observation.unverified_reason:
            unverified.append(f"{label}: {observation.unverified_reason}")
        actual = observation_signature(observation, contract)
        equivalent, diffs, fired = compare(expected, actual, contract)
        for name in fired:
            if name not in applied:
                applied.append(name)
        if not equivalent:
            divergences.append({"case": case, "diffs": diffs, "before": expected, "after": actual})

    env = dict(payload["envelope"])
    env["replay_of"] = str(Path(baseline).name)
    env["self_verification_note"] = "circular evidence; see the README limits section"
    return CheckResult(
        name=contract.name, verdict=classify(divergences, unverified),
        cases_run=len(cases), divergences=divergences, unverified=unverified,
        envelope=env, normalizers=applied, allowed=list(contract.allow),
    )


def _bounded_override(value: Any, low: int, high: int, name: str) -> int:
    """Keep CLI overrides inside the same bounds as contract-file values."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"--{name}: expected an integer")
    if not low <= value <= high:
        raise ContractError(f"--{name}: expected {low}..{high}, got {value}")
    return value


def _apply_overrides(contract: Contract, args: argparse.Namespace) -> Contract:
    budget = contract.budget
    if getattr(args, "cases", None) is not None:
        budget = replace(budget, cases=_bounded_override(args.cases, 1, MAX_CASES, "cases"))
    if getattr(args, "seed", None) is not None:
        budget = replace(budget, seed=_bounded_override(args.seed, -(2**31), 2**31 - 1, "seed"))
    if getattr(args, "timeout_ms", None) is not None:
        budget = replace(budget, timeout_ms=_bounded_override(
            args.timeout_ms, 1, MAX_TIMEOUT_MS, "timeout-ms"
        ))
    return replace(contract, budget=budget)


def _emit(text: str, output: str | None) -> None:
    if not output:
        sys.stdout.write(text)
        return
    destination = Path(output)
    if destination.is_symlink():
        raise ContractError("refusing to write through a symlink")
    destination.write_text(text, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="still",
        description="Bounded, machine-checkable evidence about what a refactor changed.",
    )
    parser.add_argument("--version", action="version", version="still 0.1.0")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(target: argparse.ArgumentParser, *, minimize_flag: bool = False) -> None:
        target.add_argument("--format", choices=FORMATS, default="text")
        target.add_argument("--output", help="write the report to a file instead of stdout")
        target.add_argument("--cases", type=int, help="override the case budget")
        target.add_argument("--seed", type=int, help="override the random seed")
        target.add_argument("--timeout-ms", type=int, dest="timeout_ms", help="override the per-case timeout")
        target.add_argument(
            "--allow-outside", action="store_true",
            help="allow targets outside the contract directory",
        )
        if minimize_flag:
            target.add_argument("--no-minimize", action="store_true", help="skip counterexample minimization")

    check = sub.add_parser("check", help="compare before and after implementations")
    check.add_argument("contract")
    common(check, minimize_flag=True)

    lock = sub.add_parser("lock", help="record the before behavior as a lockfile")
    lock.add_argument("contract")
    lock.add_argument("--output", required=True, help="lockfile destination")
    lock.add_argument("--format", choices=FORMATS, default="text")
    lock.add_argument("--cases", type=int)
    lock.add_argument("--seed", type=int)
    lock.add_argument("--timeout-ms", type=int, dest="timeout_ms")
    lock.add_argument("--allow-outside", action="store_true")

    replay = sub.add_parser("replay", help="verify current behavior against a lockfile")
    replay.add_argument("contract")
    replay.add_argument("--baseline", required=True, help="lockfile recorded before the refactor")
    replay.add_argument("--strict", action="store_true", help="fail if the declared claim changed")
    common(replay)

    init = sub.add_parser("init", help="propose a contract from the working-tree diff")
    init.add_argument("--ref", default="HEAD", help="git ref holding the before implementation")
    init.add_argument("--repo", default=".", help="repository directory")
    init.add_argument("--output", help="contract filename")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            repo = Path(args.repo).resolve()
            if not repo.is_dir():
                raise ContractError(f"not a directory: {repo}")
            path = write_proposed_contract(repo, args.ref, args.output)
            sys.stdout.write(f"wrote {path}\n")
            return 0
        if args.command == "lock":
            contract = _apply_overrides(load_contract(args.contract, allow_outside=args.allow_outside), args)
            result = run_lock(contract, args.output)
            _emit(render(result, args.format), None)
            return 0 if not result.unverified else exit_code(result)
        if args.command == "replay":
            contract = _apply_overrides(load_contract(args.contract, allow_outside=args.allow_outside), args)
            result = run_replay(contract, args.baseline, strict=args.strict)
            text = render(result, args.format)
            _emit(text, args.output)
            return exit_code(result)

        contract = _apply_overrides(load_contract(args.contract, allow_outside=args.allow_outside), args)
        result = run_check(contract, do_minimize=not args.no_minimize)
        text = render(result, args.format)
        _emit(text, args.output)
        return exit_code(result)
    except StillError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2
    except OSError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2


__all__ = ["build_parser", "main", "run_check", "run_lock", "run_replay"]
