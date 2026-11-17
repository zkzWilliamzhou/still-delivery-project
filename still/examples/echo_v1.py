#!/usr/bin/env python3
"""Command adapter fixture, version one. Reads one JSON case on stdin."""

import json
import sys


def main():
    raw = sys.stdin.read()
    try:
        value = json.loads(raw) if raw.strip() else None
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True))
        return 1
    size = len(value) if isinstance(value, (str, list, dict)) else 1
    print(json.dumps({"echo": value, "size": size}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
