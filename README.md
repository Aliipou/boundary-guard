# boundary-guard

An **architecture-boundary enforcement framework** for systems split across
separate repositories that share one philosophy. It makes "no coupling" a CI
gate, not a hope.

It lives entirely **outside** the systems it guards: it reads their source,
builds the import graph, and fails the build when a dependency points the wrong
way. It never imports, wraps, or runs AuthGate / FDK / Robotics / Banking / QFL.
**Stdlib only. Zero runtime dependencies.**

## The idea

One theory, many isolated systems. The point of splitting `authgate`, `fdk`,
`banking`, `robotics`, and `quantum-research` into different repos is that they
must not reach into each other in the wrong direction. boundary-guard proves
they don't:

```
robotics  ->  quantum_research   FORBIDDEN  (no quantum on a real-time safety path)
authgate  ->  banking            FORBIDDEN  (the kernel holds no money state)
fdk       ->  authgate           allowed    (fdk is built on top of authgate)
```

## Components (priority of engineering value)

1. **Graph Engine** — the cross-layer import graph + cycle detection.
2. **Policy DSL** — a readable `.bgpolicy` language for layers / allowed direction / forbidden edges.
3. **CI Enforcement** — `forbidden`, `cycle`, and (in `--strict`) `undeclared` findings; non-zero exit.
4. **Repository Profiles** — one master policy projected per repo.
5. **Drift Detection** — baseline + diff; new structural edges flagged early.
6. **Visualization** — Mermaid / DOT render of the policy.

## Use

```bash
# enforce (CI gate)
python -m boundary_guard check src --policy policy.example.bgpolicy
python -m boundary_guard check src --policy policy.example.bgpolicy --strict

# per-repo, via a profile
python -m boundary_guard check --policy policy.example.bgpolicy --profile profiles/authrobo.profile.json

# inspect, snapshot, detect drift
python -m boundary_guard graph    src --policy policy.example.bgpolicy
python -m boundary_guard baseline src --policy policy.example.bgpolicy --out boundaries.baseline.json
python -m boundary_guard drift    src --policy policy.example.bgpolicy --baseline boundaries.baseline.json

# visualize
python -m boundary_guard viz --policy policy.example.bgpolicy            # mermaid
python -m boundary_guard viz --policy policy.example.bgpolicy --format dot
```

## Policy DSL

```
layer authgate = authgate
layer fdk      = fdk
layer quantum_research = quantum, qkd, qfl

allow  fdk -> authgate
forbid fdk -> quantum_research : the autonomy gate is deterministic
```

`*` is a wildcard on either side; `forbid` always beats `allow`. A JSON form is
also accepted for back-compat.

## Adoption

See `ROADMAP.md` for component status and `MIGRATION.md` for how to roll this
into existing repos additively — a policy, a profile, one CI step, no code change.

## Develop

```bash
python -m unittest discover -s tests -t .
```
