# still

Find out what your refactor changed. Get a counterexample when it did.

One command, the Python standard library, no services and no account. `still` runs two implementations on the same inputs, compares the behavior you declare, and reports a bounded verdict with a minimized counterexample.

```
$ PYTHONPATH=src python3 -m still check examples/parse_price.contract.json --cases 40

DIVERGENCE  parse-price  16 of 40 cases diverged
  counterexample: "x"
    exception: before="ValueError: could not convert string to float: 'x'" after=null
  minimized in 2 reductions (3 re-runs)
Evidence envelope: 40 cases, seed 1337, generators=[strings], observed=[return, exception, stdout, stderr, exit, files], normalizers=[none], allowed=[none], timeout=2000ms.
This is bounded evidence over the stated cases, not a proof of equivalence. Untried inputs, unobserved effects and non-determinism remain outside the claim.
```

## Install

```bash
git clone <your-fork-url> && cd still
python3 -m pip install .
```

Or run straight from the checkout:

```bash
PYTHONPATH=src python3 -m still check examples/parse_price.contract.json
```

Python 3.10 or newer. No runtime dependencies.

## Why this exists

An agent rewrites a function. The diff reads well. Tests pass. A reviewer still asks whether anything observable changed. Today that question gets a hand-written differential script, a snapshot, or a shrug. Each option either costs more than the refactor or ignores side effects in silence.

`still` makes the claim explicit. A contract names what counts as behavior: return value, exception, stdout, stderr, exit code, and files written to the working directory. The verdict names how many cases it tried and which fields it normalized. A clean result has a visible boundary.

## Your first contract

```json
{
  "schema_version": "1.0",
  "name": "sum-clean-refactor",
  "adapter": "python",
  "before": "sum_v1.py::total",
  "after": "sum_v2.py::total",
  "inputs": {
    "seed": [[], [1], [1, 2, 3], [-1, 1]],
    "generators": [
      {"kind": "ints", "min": -50, "max": 50, "count": 30}
    ]
  },
  "observe": ["return", "exception", "stdout", "stderr", "exit", "files"],
  "normalize": [],
  "allow": [],
  "budget": {"cases": 40, "timeout_ms": 2000, "seed": 7}
}
```

Run it:

```bash
still check sum.contract.json
still check sum.contract.json --format sarif --output still.sarif
still check sum.contract.json --format markdown --output certificate.md
```

Generate a starter contract from changed functions in your working tree:

```bash
still init --ref HEAD --output refactor.contract.json
```

`init` reads `git diff`, finds changed top-level Python functions, and points `before` at the `HEAD` version with `path.py@HEAD::func`.

## Behavior lockfiles

Record behavior before a refactor, then replay afterwards. This is the workflow used to verify `still`'s own architecture refactor.

```bash
still lock self.contract.json --output behavior.lock.json
# apply the refactor
still replay self.contract.json --baseline behavior.lock.json --strict
```

The lockfile stores cases and signatures in portable JSON. A digest of the declared claim catches contract drift. `--strict` fails when the claim changed. Replay prints a circularity note: the lockfile and the runner share code, so treat the result as evidence rather than certification.

## Verdicts and exit codes

| Verdict | Meaning | Exit code |
| --- | --- | --- |
| `NO_DIVERGENCE_FOUND` | No difference appeared in the stated corpus | 0 |
| `DIVERGENCE` | At least one case differed; a minimized counterexample is included | 1 |
| `UNVERIFIED` | A case timed out, hit a capture cap, or could not be compared | 2 |
| `LOCKED` | `still lock` wrote a behavior lockfile | 0 |

`UNVERIFIED` never collapses into a pass. CI can catch it.

## CI

```yaml
- run: python -m pip install .
- run: still check refactor.contract.json --format sarif --output still.sarif
- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: still.sarif
```

`still` writes SARIF 2.1.0 with one result per divergence and one warning per unverified case. See `.github/workflows/ci.yml` for the workflow this repository uses.

## Adapters

| Adapter | Target syntax | What it observes |
| --- | --- | --- |
| `python` | `path.py::func` or `path.py@REF::func` | return, exception, stdout, stderr, exit, files |
| `command` | `path/to/executable` or `path@REF` | stdout, stderr, exit, files |

The command adapter sends one JSON case on stdin. Any language works. It receives the same subprocess limits, scrubbed environment and private working directory.

## Normalizers

Declare every transformation. The report names the rules that fired.

| Kind | Effect |
| --- | --- |
| `strip` | Trim leading and trailing whitespace on a string field |
| `lower` | Lowercase a string field |
| `sort_lines` | Sort the lines of a string field |
| `regex_replace` | Replace a declared pattern with a declared replacement |
| `ignore_field` | Drop a field from both sides |
| `float_tolerance` | Compare numbers with declared absolute and relative tolerance |

`allow` lists fields whose divergence you accept. Both the allowed list and the applied normalizers appear in the evidence envelope, so a clean verdict cannot hide a suppressed difference.

## Honest limits

Read these before you rely on a verdict.

- **Evidence, not proof.** Arbitrary equivalence is undecidable. The claim covers the cases run, the generators used and the fields observed.
- **No hidden cleanup.** Volatile data such as timestamps, UUIDs and temporary paths creates divergences unless you declare a normalizer.
- **Subprocess, not a sandbox.** Each side gets a fresh process, a scrubbed environment, a private temp directory, CPU and address-space limits, an output cap and a process-group kill on timeout. The Python adapter also blocks `socket.socket`. The command adapter has no in-child network guard. Use a container for hostile code.
- **Side effects stay narrow.** The tool observes files written inside the private working directory. It does not observe databases, network calls, clocks or external services.
- **Self-verification is circular.** A lockfile and the runner share code. Independent external fixtures and the full test suite sit alongside it.
- **No star guarantee.** Stars measure attention. This project has zero stars at the time of writing.

## Prior art

Differential testing, property-based testing (Hypothesis, QuickCheck, fast-check), mutation testing (Stryker, mutmut, gremlins), snapshot testing (Jest), API compatibility tools (Revapi, japicmp), automated test generation (EvoSuite, Pynguin, Diffblue) and delta debugging (C-Reduce) all exist. `still` does not replace them.

As of 12 November 2026, bounded public research did not locate a zero-dependency, drop-in CLI combining diff-scoped contract proposals, differential execution, declared observation and normalization, counterexample minimization, a portable behavior lockfile and CI-native reporting for arbitrary application code. That statement describes a search result, not a claim of absolute novelty. Found prior art that matches the integrated workflow? Open an issue. The project will cite it.

The full report with sources and dates lives in `novelty_landscape.md`.

## Development

```bash
python -m pip install -q ruff mypy pytest bandit
python -m ruff check src tests examples scripts
python -m mypy src/still
python -m bandit -q -r src/still
python -m pytest tests -q
PYTHONPATH=src python3 scripts/cli_matrix.py
PYTHONPATH=src python3 scripts/verify_function_preservation.py verify
```

The last command replays a behavior lockfile recorded before the architecture pass. It is the hard gate for "no function changed": seven deterministic report hashes must stay byte-identical and both strict replays must report no divergence.

See `PLAN.md`, `WORKFLOW.md`, `REVIEW_LOG.md`, `LEDGER.md`, `CONTEXT.md`, `GLOSSARY.md` and `docs/adr/` for the design, the agent gates, the ten review rounds, the closed ledger and the architecture decision record. The ranked before/after diagrams from the architecture pass are in `architecture-review.html` in the delivery bundle.

## License

MIT. See `LICENSE`.
