# still

A behavior-contract verifier for Python refactoring and AI-generated changes.

## Install

```bash
pip install .
```

## Usage

```bash
# Check if two implementations are behavior-equivalent
still check examples/parse_price.contract.json

# Lock current behavior for later comparison
still lock examples/parse_price.behavior.lock

# Replay a locked contract against new implementation
still replay examples/parse_price.behavior.lock

# Initialize a contract from git diff
still init
```

## Sample Output

```
DIVERGENCE  parse_price  1 of 240 cases diverged
  counterexample: {"s": "$0"}
  before: {"return": 0.0, "exit": 0}
  after:  {"return": null, "exit": 0}
  minimized from 4 chars to 2 chars in 6 reductions

Evidence envelope: 240 cases, seed 1337, generators=[strings],
  observed=[return, exception, exit, stdout, stderr, files],
  normalizers=[none], timeout=2000ms, both sides in scrubbed temp dirs.
This is bounded evidence, not a proof of equivalence.
```

## Why

When an AI agent rewrites a function, the diff may look clean and tests may pass, but did anything observable change? `still` makes the claim explicit by running both implementations on generated inputs and comparing declared observables.

## Documentation

See [PLAN.md](./PLAN.md) and [WORKFLOW.md](./WORKFLOW.md) for detailed documentation.

## License

MIT License - see [LICENSE](./LICENSE) file.