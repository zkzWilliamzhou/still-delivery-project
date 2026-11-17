# Review log

Ten rounds. Each entry states the command, the output that was actually seen, the
finding, and the fix. A round that found nothing says so with its command. The
boss (P01) re-ran the whole gate set after each fix; a round closes only on
fresh output.

The QA toolchain did not persist between sandbox turns in this environment, so
several commands below are preceded by `python3 -m pip install -q ruff pytest
mypy bandit`. That is an environment fact, not a change to the program.

## R1 - Static lint and dead code

Command: `ruff check src tests examples`

Output at the time: 21 findings. One was a real functional defect; the rest
were style, unused imports and dead code.

Finding: the first pass was not good enough to close the round. The functional
defect was fixed and the tree re-linted before R2 opened. The detailed
line-by-line output belongs to an earlier turn; the fresh evidence for the
final tree is below.

Fix verification on the final tree:
`ruff check src tests examples scripts` -> `All checks passed!`

## R2 - Type and interface correctness

Command: `python3 -m mypy --no-incremental --cache-dir=/tmp/mc_inputs2 src/still/inputs.py`

Output:
```
src/still/inputs.py:26: error: Incompatible types in assignment (expression has type "float", variable has type "int")  [assignment]
Found 1 error in 1 file (checked 1 source file)
```

Finding: `low, high` was bound to `int` in the `ints` branch and rebound to
`float` in the `floats` branch. A real typing defect at the generator seam.

Fix: renamed the float locals to `low_f, high_f` in `inputs.py`.

Verification: `python3 -m mypy --no-incremental --cache-dir=/tmp/mc_full src/still`
-> `Success: no issues found in 11 source files`.

## R3 - Security and unsafe execution

Command: `python3 -m bandit -q -r src/still -f json -o /tmp/bandit.json`

Output: 10 LOW findings, 0 MEDIUM, 0 HIGH. B404 (two subprocess imports), B607
(three partial executable paths), B603 (four subprocess calls), B311 (one
pseudo-random generator).

Finding: `git` was invoked by bare name, so PATH was an implicit trust input.
`diffscope.py` accepted git-reported paths with only a `startswith("..")`
check, which does not catch absolute paths or embedded `..` parts. The random
module was used for test-case generation with no recorded justification.

Fix:
- Added `src/still/gitbin.py`, an `lru_cache` resolver returning `shutil.which("git")`
  or a `ContractError`. Both `git show` sites and both diffscope git calls use it.
- Added `shell=False` at every subprocess site, with `# nosec B603` and a comment
  explaining the fixed argv and validated ref/path.
- Replaced the weak path filter in `diffscope.py` with `resolve().relative_to(root)`
  plus absolute-path and `..` part rejection, and a NUL check.
- Marked `random.Random(seed)` as a deliberate reproducibility choice, not a
  security decision.
- Cleaned the `# nosec` comments so bandit parses no stray words.

Verification: `python3 -m bandit -q -r src/still -f json` -> `results: 0 errors: 0`
with all severity totals at 0. `ruff` clean, `mypy` clean on 12 source files.

## R4 - Unit and regression behavior

Command: `python3 -m pytest tests -q`

Output: 1 failure, 41 passed.
```
FAILED tests/test_core.py::test_cases_are_deduplicated_and_capped
assert 3 == 5  # where 3 = len([1, 2, 3])
```

Finding: the test asserted the case budget is a target size. `build_cases`
deduplicates a seeded corpus, so a generator over `{1,2,3}` can only yield 3
distinct cases. The test was wrong, not the implementation. It also never
exercised the cap.

Fix: split into `test_cases_are_deduplicated` (expects 3) and
`test_case_budget_caps_a_wide_generator` (200 unique strings, cap 7). Wrapped
one long line for E501.

Verification: `python3 -m pytest tests -q` -> 42 passed;
`ruff check src tests examples` -> `All checks passed!`.

## R5 - Malformed input and robustness

Command: `python3 /tmp/probe_robust.py` (adversarial probe over contract
parsing, CLI overrides, normalizer reporting and lockfile replay).

Output, abridged:
```
observe contains a list                       -> ContractError: unknown field
observe contains a dict                       -> ContractError: unknown field
seed contains a nested huge value             -> NO ERROR RAISED
generator count too large                     -> ContractError: ... 0..100000
normalize field unhashable                    -> ContractError: must be one of
CLI --cases/--timeout override bounds         -> NOT VALIDATED: cases=1000000000 timeout=0
float_tolerance fires but is reported         -> equal=True applied=[]
lockfile signature element type               -> NO ERROR RAISED
```

Findings, four of them real:
1. `--cases` and `--timeout-ms` bypassed the contract-file bounds entirely. A
   CLI caller could request 1e9 cases or a zero timeout.
2. A `float_tolerance` rule that widened a comparison was invisible in the
   evidence envelope, so a clean verdict could hide a loosened claim.
3. A lockfile with a non-object signature element reached replay without error.
4. `cases_run` reported the planned corpus size even when the divergence cap
   truncated the loop.

Also recorded without a fix: a deeply nested seed value is not size-bounded at
parse time. It is bounded at execution by the worker's result cap and the
subprocess output cap, so this is a documented limitation rather than an
unbounded read.

Fix:
- `cli.py`: added `_bounded_override`, applied to cases (1..MAX_CASES), seed
  (int32 range) and timeout-ms (1..MAX_TIMEOUT_MS).
- `equivalence.py`: `apply_normalizers` now reports a `float_tolerance` label
  when its field is present in the result.
- `lockfile.py`: each signature must be a JSON-safe object under 200 KB; lengths
  must match the case list.
- `cli.py`: `attempted` counter is recorded and used for `cases_run` and
  `envelope["cases_attempted"]`.
- Added `tests/test_robustness.py` with 19 tests covering all of the above.

Verification: 19 new tests pass; `ruff`, `mypy`, `bandit` clean; full suite 61
passed.

## R6 - CLI contract and exit codes

Commands: `python3 -m still check ...` across text, json, sarif, markdown;
`lock`, `replay`, `init --help`, `--version`; `--format` and `--output`.

Output: 17 contract checks, all passing. Verified exit 0 for a clean refactor,
exit 1 for a divergence, exit 2 for a malformed contract or out-of-range
override, with no traceback on user error. A minimized counterexample was
printed (`"x"`, 2 reductions, 3 re-runs).

Finding: the README's sample output was invented. It showed 68 cases, a fake
`__still_unserializable__` return and 11 re-runs. Running the real command gave
40 cases, a `ValueError` exception field and 2 reductions.

Fix: replaced the README sample with the literal output of
`PYTHONPATH=src python3 -m still check examples/parse_price.contract.json --cases 40`.
Added `scripts/cli_matrix.py`, a repeatable 17-check matrix over every command,
format and exit code, and wired it into CI.

Verification: `PYTHONPATH=src python3 scripts/cli_matrix.py` ->
`17/17 CLI contract checks passed`.

## R7 - Resource limits and runaway processes

Command: `python3 -m pytest tests/test_resources.py -q`

Output: 2 failures out of 9. Both were test-authoring mistakes, not program
defects:
```
FAILED test_child_process_group_is_killed_on_timeout - assert False is True
FAILED test_many_files_are_capped_and_unverified - '__truncated__' is None
```

Findings:
1. The child-process test spawned a sleeper and returned immediately, so the
   parent never timed out. It asserted `timed_out is True` on a successful run.
2. The many-files test used `f'f{{i}}'` inside a generated string, so all 200
   writes went to one literal file named `f{i}`.

Fix: rewrote test 1 so the parent also sleeps, times out, and then scans `/proc`
for a unique marker in any surviving child cmdline. Rewrote test 2 to build
filenames with string concatenation. Removed two unused imports flagged by ruff.

Verification: 9 resource tests pass; full suite 70 passed. The tests now cover
timeout, child process-group kill, stdout cap, file-count cap, environment
scrubbing, socket disabling, non-executable command targets and contract size
bounds.

## R8 - Dogfooding, docs, CI and installation

Command: `python3 -m pip install -q --no-deps --target /tmp/still_install .`
then `PYTHONPATH=/tmp/still_install python3 -m still --version`.

Output: `No module named still`. The wheel was `UNKNOWN-0.0.0-py3-none-any.whl`
of 1795 bytes. Cause: the system Python ships setuptools 59.6.0, which cannot
read PEP 621 metadata from `pyproject.toml`; a leftover `UNKNOWN.egg-info`
directory poisoned subsequent builds.

Other R8 output: the em-dash and slop scan over README, CONTEXT, GLOSSARY, ADR,
PLAN and WORKFLOW returned no hits; `.github/workflows/ci.yml` parsed with one
job and nine steps.

Findings: a user following `pip install .` on an older setuptools got an empty
package. The deprecated `License ::` classifier produced a build warning.

Fix:
- Added `setup.py` as a compatibility shim with name, version and the `src`
  layout, explicitly documented as secondary to `pyproject.toml`.
- Added `tests/test_packaging.py` to enforce that the shim and pyproject agree
  on name and version, that the src layout is declared, that the README states
  its limits, and that CI runs all four checkers.
- Changed `license = {text = "MIT"}` to `license = "MIT"` and removed the
  deprecated classifier.
- Removed the stale egg-info directories and added `*.egg-info/` to `.gitignore`.

Verification:
```
python3 -m pip install -q --no-deps --target /tmp/still_install7 .
PYTHONPATH=/tmp/still_install7 python3 -m still --version   -> still 0.1.0
```
A `--target` install needs that `PYTHONPATH` for the generated console script too;
without it the script cannot see the target directory. A normal install was
checked separately on the final tree:
```
python3 -m pip install -q --no-deps --force-reinstall .
still --version                                          -> still 0.1.0
python3 -c "import still; print(still.__file__)"         -> .../dist-packages/still/__init__.py
```
Full gates clean; 74 tests passed; CLI matrix 17/17.

## R9 - Architecture deepening, with a hard function-preservation gate

Before touching a file, the boss recorded a behavior baseline:
`PYTHONPATH=src python3 scripts/verify_function_preservation.py record` ->
7 deterministic report hashes and 2 behavior lockfiles stored in `.golden/`.

The `improve-codebase-architecture` pass produced
`/tmp/architecture-review-20261113-104700.html` (a copy also sits at
`/data/workspace/architecture-review.html`). Three candidates were ranked:

- C1 (Strong): fold the duplicate signature selector and the local envelope and
  verdict helpers into one deep claim module, `evidence.py`, behind
  `build_envelope` and `classify`.
- C2 (Worth exploring): a shared `run_corpus` loop. Deferred: only two adapters
  exist, so the seam would be hypothetical and the interface wide.
- C3 (Speculative): split `report.py` into four formatter modules. Rejected by
  the deletion test; `report.py` is already deep with a narrow `render` interface.

The grilling loop ran inline under a standing instruction to finish without a
pause. Its decisions: keep all four verdict strings and all six observables;
`evidence.py` must not import `execution`; new tests must cross the same seam;
the baseline lockfile is the acceptance test.

Changes applied: added `src/still/evidence.py`; routed `run_check`, `run_lock`
and `run_replay` through `build_envelope` and `classify`; deleted the duplicate
`signature_from_observation` from `equivalence.py`; deleted the unused
`Observation.from_dict` and a dead `os.getpid()` line; added `claim module` and
`adapter loop` to `GLOSSARY.md`; added `tests/test_evidence.py`.

Boss verification, the hard gate:
```
PYTHONPATH=src python3 scripts/verify_function_preservation.py verify
PASS check clean / parse_price / parse_price_no_minimize / command / self
PASS check clean_sarif / clean_markdown          (identical report)
PASS replay clean / replay self                  (no divergence)
All 7 reports identical and 2 lockfile replays clean.
No observable function changed during the architecture pass.
```
Also: `ruff` clean, `mypy` clean on 13 source files, `bandit` 0 findings,
74 tests passed, CLI matrix 17/17. The disclaimer required by ADR-0001 stayed
in every output format.

## R10 - Post-architecture audit and final closure

Commands:
```
grep -rn "signature_from_observation|from_dict|cli.envelope|def _verdict" src tests scripts examples
grep -rn "shell=True|os.system|eval(|exec(|pickle.loads" src
grep -rni "todo|fixme|placeholder|not implemented" src tests
python3 -m ruff check src tests examples scripts
python3 -m mypy --no-incremental --cache-dir=/tmp/mc_final src/still
python3 -m bandit -q -r src/still
python3 -m pytest tests -q
PYTHONPATH=src python3 scripts/cli_matrix.py
PYTHONPATH=src python3 scripts/verify_function_preservation.py verify
```

Output: no stale references to removed units, no unsafe patterns, no TODO or
placeholder markers. Static gates clean: `All checks passed!`,
`Success: no issues found in 13 source files`, bandit 0 findings.

Finding: the new `tests/test_evidence.py` failed twice on invalid fixtures --
`normalize` used a non-existent `trim` kind, and `allow` used a dict where the
schema requires field-name strings. Both were test-authoring errors caught by
`parse_contract`; the boss sent the test back twice.

Fix: `trim` -> `strip`, `allow=[{"field":"stderr",...}]` -> `allow=["stderr"]`,
with matching assertions.

Verification: 82 tests passed, CLI matrix 17/17, preservation 7 identical
reports and 2 clean strict replays. All ten rounds closed with fresh output.

## Final gate set

| Gate | Command | Result |
| --- | --- | --- |
| Lint | `ruff check src tests examples scripts` | All checks passed |
| Types | `mypy src/still` | 13 files, no issues |
| Security | `bandit -q -r src/still` | 0 findings |
| Tests | `pytest tests -q` | 82 passed |
| CLI contract | `scripts/cli_matrix.py` | 17/17 |
| Function preservation | `scripts/verify_function_preservation.py verify` | 7 hashes identical, 2 strict replays clean |
| Install | `pip install --target <dir> .` then `still --version` | `still 0.1.0` |

The 82 tests, the 17 CLI checks and the preservation harness are repeatable.
The 105,000-star objective is a growth hypothesis in `PLAN.md` Section 7, not
a verified result; this repository has zero stars.
