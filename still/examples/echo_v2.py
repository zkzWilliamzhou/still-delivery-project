#!/usr/bin/env python3
"""Command adapter fixture, version two. Different code, same observable output."""

import json
import sys


def main():
    data = sys.stdin.read()
    try:
        item = json.loads(data) if data.strip() else None
    except json.JSONDecodeError as error:
        sys.stdout.write(json.dumps({"error": str(error)}, sort_keys=True) + "\n")
        return 1
    length = len(item) if isinstance(item, (str, list, dict)) else 1
    sys.stdout.write(json.dumps({"echo": item, "size": length}, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
