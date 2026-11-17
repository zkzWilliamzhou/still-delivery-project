"""Child process that loads one Python target and records its result.

The parent writes a JSON request to a file and passes that path as argv[1].
This module never prints the target's result to stdout, because stdout is an
observable field that belongs to the target under test.
"""

from __future__ import annotations

import importlib.util
import json
import socket
import sys
from pathlib import Path
from typing import Any

MAX_RESULT_BYTES = 1_000_000


class _BlockedSocket(socket.socket):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise OSError("network access is disabled by still")


def _json_safe(value: Any) -> Any:
    """Convert a return value into something JSON can carry without losing shape."""
    try:
        encoded = json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError, RecursionError):
        return {"__still_unserializable__": repr(value)[:512]}
    if len(encoded) > MAX_RESULT_BYTES:
        return {"__still_truncated__": encoded[:512]}
    return json.loads(encoded)


def _load_function(module_path: str, function_name: str) -> Any:
    spec = importlib.util.spec_from_file_location("_still_target", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    if not hasattr(module, function_name):
        raise AttributeError(f"{module_path} has no function {function_name!r}")
    return getattr(module, function_name)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        return 2
    request_path = Path(argv[1])
    request = json.loads(request_path.read_text(encoding="utf-8"))
    result_path = Path(request["result_path"])

    # Blocks the common socket entry point before target code is imported.
    socket.socket = _BlockedSocket  # type: ignore[assignment,misc]

    result: dict[str, Any] = {"return": None, "exception": None}
    try:
        function = _load_function(request["module"], request["function"])
        result["return"] = _json_safe(function(request["case"]))
    except BaseException as exc:
        result["exception"] = f"{type(exc).__name__}: {str(exc)[:512]}"

    payload = json.dumps(result, ensure_ascii=False, default=str)
    if len(payload.encode("utf-8")) > MAX_RESULT_BYTES:
        payload = json.dumps({"return": None, "exception": "StillError: result too large"})
    result_path.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
