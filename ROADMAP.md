# boundary-guard — implementation roadmap

Built in priority of **engineering value**, not demo value. Graph + Policy +
Enforcement are the load-bearing core; visualization is last on purpose.

| # | Component | Status | What it gives |
|---|-----------|--------|---------------|
| 1 | **Graph Engine** (`graph.py`) | ✅ done | Builds the cross-layer import graph; layer adjacency; cycle detection. |
| 2 | **Policy DSL** (`policy.py`) | ✅ done | Readable `.bgpolicy` language (+ JSON loader): layers, allowed direction, forbidden edges with reasons. |
| 3 | **CI Enforcement** (`enforce.py`, `cli.py`, workflow) | ✅ done | `forbidden` / `cycle` / `undeclared` findings; non-zero exit; drop-in GitHub Action. |
| 4 | **Repository Profiles** (`profiles.py`) | ✅ done | One master policy projected per repo to the layers that repo can see. |
| 5 | **Drift Detection** (`drift.py`) | ✅ done | Baseline snapshot + diff; new cross-layer edges flagged before they're ever forbidden. |
| 6 | **Visualization** (`viz.py`) | ✅ minimal | Mermaid / DOT render of the policy. Demo value only. |

## Design constraints (held throughout)

- **Outside runtime, always.** boundary-guard reads source; it never imports, wraps, or runs AuthGate / FDK / Robotics / Banking / QFL.
- **Zero runtime dependencies.** Stdlib only (`ast`, `json`, `argparse`, `pathlib`). Tests use stdlib `unittest`.
- **No redesign of existing repos.** Adoption is additive: a policy file, a profile, one CI step.
- **No philosophy rewrite.** The DSL encodes the separation already agreed; it does not introduce new theory.

## Next increments (when needed, still in-scope)

- `--format sarif` on `check` for GitHub code-scanning annotations.
- Module-level (not just layer-level) graph for finer reports.
- A `pre-commit` hook wrapper.
- Cross-repo aggregation: collect each repo's edges and validate the federation graph centrally.
