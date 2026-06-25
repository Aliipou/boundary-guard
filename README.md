# boundary-guard

Enforce architecture boundaries across **separate repositories** that share one
philosophy. Makes "no coupling" a CI gate, not a hope.

One theory, many isolated systems. The whole point of splitting `authgate`,
`fdk`, `banking`, `robotics`, and `quantum-research` into different repos is that
they must **not** reach into each other in the wrong direction. This tool proves
they don't.

## What it does

Maps every `.py` file to a **layer** (by the top-level package it lives in),
parses its imports, and fails the build if any import crosses a **forbidden
edge** — e.g. a robot control loop importing quantum research, or the capability
kernel importing financial state.

```
robotics  ->  quantum_research   FORBIDDEN  (no quantum on a real-time safety path)
authgate  ->  banking            FORBIDDEN  (the kernel holds no money state)
fdk       ->  authgate           allowed    (fdk is built on top of authgate)
```

Stdlib only. No dependencies. Deterministic.

## Use

```bash
# check one or more source roots against a policy
python boundary_guard.py path/to/src --policy policy.example.json

# self-test (proves it catches the forbidden edge and ignores the allowed one)
python selftest.py
```

Exit code is `1` on any violation, so it drops straight into CI (see
`.github/workflows/ci.yml`).

## Per-repo adoption

Copy `boundary_guard.py` + a trimmed `policy.json` into each repo, and add a CI
step that runs it against that repo's source. Each repo only declares the layers
it can legitimately see. Direction of dependency is one-way and explicit:

```
philosophy        (freedom-theory)      ── imports nothing below it
   ▲
authgate          (authgate-kernel)     ── classical + PQC, no money, no quantum
   ▲
fdk               (freedom-decision-kernel)
   ▲                         ▲
banking                   robotics       ── depend on authgate; never the reverse
                                          ── never on quantum_research or analytics

quantum_research  (qfl / qkd)            ── research sandbox, T3, no edge into prod
observability     (analytics)            ── observes everything, controls nothing
```

## Policy format

`policy.example.json` — `layers` map each layer to the import roots that belong
to it; `forbidden` lists one-way edges that must never exist, each with a `why`
that gets printed on violation. `"to": "*"` forbids importing *any* other layer
(used for the pure philosophy layer).
