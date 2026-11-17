"""Portable behavior lockfiles recorded before a refactor and replayed after it."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .model import ContractError, SCHEMA_VERSION, digest

MAX_LOCK_BYTES = 8_000_000
LOCK_KEYS = {"schema_version", "contract_digest", "cases", "signatures", "envelope"}


def write_lock(path: str | Path, contract: Any, cases: list[Any],
               signatures: list[dict[str, Any]], envelope: dict[str, Any]) -> dict[str, Any]:
    """Write a deterministic lockfile and return the payload."""
    if len(cases) != len(signatures):
        raise ContractError("lock: cases and signatures must have the same length")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "contract_digest": contract.digest(),
        "cases": cases,
        "signatures": signatures,
        "envelope": envelope,
    }
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str)
    if len(text.encode("utf-8")) > MAX_LOCK_BYTES:
        raise ContractError("lock: payload exceeds the size cap")
    destination = Path(path)
    if destination.is_symlink():
        raise ContractError("lock: refusing to write through a symlink")
    destination.write_text(text + "\n", encoding="utf-8")
    return payload


def read_lock(path: str | Path) -> dict[str, Any]:
    """Read and validate a lockfile."""
    source = Path(path)
    if source.is_symlink():
        raise ContractError("lock: refusing to read through a symlink")
    if not source.is_file():
        raise ContractError(f"lockfile not found: {source}")
    size = source.stat().st_size
    if size > MAX_LOCK_BYTES:
        raise ContractError(f"lockfile too large: {size} bytes")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"lockfile could not be read: {exc}") from exc
    if not isinstance(payload, dict):
        raise ContractError("lock: expected a JSON object")
    if set(payload) != LOCK_KEYS:
        raise ContractError(f"lock: expected keys {sorted(LOCK_KEYS)}, got {sorted(payload)}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ContractError("lock: unsupported schema version")
    cases, signatures = payload["cases"], payload["signatures"]
    if not isinstance(cases, list) or not isinstance(signatures, list):
        raise ContractError("lock: cases and signatures must be lists")
    if len(cases) != len(signatures) or not cases:
        raise ContractError("lock: cases and signatures must be non-empty and equal in length")
    for index, signature in enumerate(signatures):
        if not isinstance(signature, dict):
            raise ContractError(f"lock: signatures[{index}] must be an object")
        try:
            if len(json.dumps(signature, sort_keys=True, default=str)) > 200_000:
                raise ContractError(f"lock: signatures[{index}] is too large")
        except (TypeError, ValueError) as exc:
            raise ContractError(f"lock: signatures[{index}] is not JSON-safe") from exc
    if not isinstance(payload["envelope"], dict):
        raise ContractError("lock: envelope must be an object")
    if not isinstance(payload["contract_digest"], str) or len(payload["contract_digest"]) != 64:
        raise ContractError("lock: invalid contract digest")
    return payload


def lock_matches_contract(payload: dict[str, Any], contract: Any) -> bool:
    """Compare the declared claim identity without trusting a filename."""
    return payload["contract_digest"] == digest(contract.to_dict())
