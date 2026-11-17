"""Resolve the git executable to an absolute path before subprocess use.

Bandit B607 flags partial executable names because PATH can be attacker
controlled. Both `git show` call sites go through this resolver, and both
validate the ref and path arguments before constructing an argv list. No shell
is involved.
"""

from __future__ import annotations

import shutil
from functools import lru_cache

from .model import ContractError


@lru_cache(maxsize=1)
def git_binary() -> str:
    """Return an absolute path to git, or raise a contract error."""
    found = shutil.which("git")
    if not found:
        raise ContractError("git executable not found on PATH")
    return found
