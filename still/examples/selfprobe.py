"""Standalone probe used to verify that the still architecture refactor changed no function.

The probe loads the installed still package from this repository's src tree and
exercises contract parsing, case generation, equivalence comparison and report
rendering in one deterministic call. A lockfile records its behavior before the
refactor; replay compares the refactored package against that record.
"""

import json
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from still.equivalence import compare  # noqa: E402
from still.inputs import build_cases, case_label  # noqa: E402
from still.model import parse_contract  # noqa: E402
from still.report import NO_DIVERGENCE, CheckResult, render  # noqa: E402


def probe(case):
    seed = case if isinstance(case, list) else [case]
    document = {
        "schema_version": "1.0",
        "name": "probe",
        "adapter": "python",
        "before": "placeholder_a.py::f",
        "after": "placeholder_b.py::f",
        "inputs": {
            "seed": seed,
            "generators": [
                {"kind": "strings", "alphabet": "ab01", "min_len": 0, "max_len": 4, "count": 6}
            ],
        },
        "observe": ["return", "exception"],
        "normalize": [],
        "allow": [],
        "budget": {"cases": 12, "timeout_ms": 1000, "seed": 3},
    }
    contract = parse_contract(document, Path(__file__).resolve().parent)
    cases = build_cases(contract)
    labels = [case_label(item) for item in cases[:4]]
    signature = {"return": labels, "exception": None}
    equivalent, diffs, applied = compare(signature, signature, contract)
    result = CheckResult(
        name=contract.name, verdict=NO_DIVERGENCE, cases_run=len(cases),
        envelope={"seed": contract.budget.seed},
    )
    rendered = render(result, "json")
    return {
        "labels": labels,
        "equivalent": equivalent,
        "diffs": diffs,
        "normalizers": applied,
        "report_verdict": json.loads(rendered)["verdict"],
        "count": len(cases),
    }
