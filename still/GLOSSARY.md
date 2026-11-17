# Glossary

Words used in the code, the contracts and the architecture notes. Keep these meanings stable.

| Term | Meaning |
| --- | --- |
| contract | A JSON file declaring two implementations, the inputs to try, the observables to compare, the normalization rules and the case budget |
| case | One input value passed to both implementations |
| observable | A declared field recorded from each run: `return`, `exception`, `stdout`, `stderr`, `exit`, `files` |
| observation | The full record of one run of one implementation on one case |
| signature | The subset of an observation selected by a contract's `observe` list |
| divergence | A case where the two signatures differ under the declared equivalence relation |
| counterexample | A divergent case reduced by delta debugging until the divergence still holds |
| evidence envelope | The cases run, generators, seed, timeout, observed fields, normalizers and allowed divergences that bound a verdict |
| behavior lockfile | A portable record of signatures for a set of cases, written before a refactor and replayed afterwards |
| adapter | A seam that runs one implementation: `python` loads a function, `command` runs an executable that reads JSON on stdin |
| verdict | `NO_DIVERGENCE_FOUND`, `DIVERGENCE` or `UNVERIFIED` |
| claim module | `evidence.py`: the deep module that owns the evidence envelope and verdict classification behind one interface, so `check`, `lock` and `replay` stay thin adapters |
| adapter loop | One of the three thin CLI orchestration loops (`check`, `lock`, `replay`) that consume the claim module's interface |
