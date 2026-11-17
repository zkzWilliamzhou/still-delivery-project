"""still: bounded behavior evidence for refactors and AI-generated changes."""

from .model import Contract, ContractError, StillError, load_contract, parse_contract
from .report import CheckResult, NO_DIVERGENCE, DIVERGENCE, UNVERIFIED

__version__ = "0.1.0"

__all__ = [
    "DIVERGENCE",
    "NO_DIVERGENCE",
    "UNVERIFIED",
    "CheckResult",
    "Contract",
    "ContractError",
    "StillError",
    "__version__",
    "load_contract",
    "parse_contract",
]
