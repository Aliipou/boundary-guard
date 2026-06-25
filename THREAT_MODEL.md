# boundary-guard — threat model & adversarial review

> Posture: assume the system is wrong and try to kill it. A boundary enforcer
> that can be bypassed is worse than none — it sells false confidence. Every
> attack below is encoded as a test (`tests/test_adversarial*.py`); a regression
> that reopens one fails CI.

## Assets, boundary, attacker

- **Asset:** the architectural invariant "layer A must not depend on layer B."
- **Trust boundary:** boundary-guard reads source statically. It is *outside* the
  guarded runtimes — it never imports or executes them.
- **Attacker:** a developer or a prompt-injected agent with commit access who
  wants a forbidden cross-layer dependency to exist while keeping CI green.

## Invariants

- **INV-1** A forbidden edge present in scanned source is always reported.
- **INV-2** A forbidden dependency cannot be hidden by *static obfuscation*
  (dynamic import with a constant arg, an unmapped glue module, a layer-named dir).
- **INV-3** A file that cannot be analyzed is surfaced (`--strict`), never silently skipped.
- **INV-4** A healthy graph yields zero findings (false-positive rate ≈ 0).
- **INV-5** Output is deterministic and stable across runs.
- **INV-6** A malformed or self-defeating policy is rejected, not silently honored.

## Attack catalog (status)

| # | Wave | Attack | Status |
|---|------|--------|--------|
| 1 | 1 | `importlib.import_module("quantum")` (constant arg) | ✅ caught (dynamic-import resolution) |
| 2 | 1 | `__import__("quantum")` | ✅ caught |
| 3 | 1 | aliased `import_module as im` / `import importlib as Y` | ✅ caught |
| 4 | 1 | launder forbidden dep through an unmapped `shared/` module | ✅ caught (`(unscoped)` source + blanket forbid) |
| 5 | 1 | hide imports in an unparseable file | ✅ surfaced as `unanalyzable` (`--strict`) |
| 6 | 1 | spoof into a layer-named dir lacking a forbid edge | ✅ closed by `forbid * -> quantum_research` |
| 7 | 1 | shadow a forbid with a permissive `allow` | ✅ forbid always wins |
| 8 | 1 | `allow * -> *` to neuter drift detection | ✅ rejected by policy validation |
| 9 | 1 | duplicate roots across layers / typo'd layer name | ✅ rejected by policy validation |
| 10 | 3 | transitive coupling **within** a repo (A→mid→C) | ✅ the forbidden hop is flagged at its edge |
| 11 | 2 | false positive on deep nested / fully-allowed graphs | ✅ zero findings |
| 12 | 5 | scale to hundreds of files | ✅ fast + deterministic |

## Known limitations (what boundary-guard does NOT detect)

Static, single-repo import analysis cannot see everything. These are real and
must be covered by other controls — do not claim the guard covers them:

- **Cross-repo transitive coupling (Wave 3).** If repo A imports a shared lib B
  (allowed) and B internally imports the quantum sandbox, scanning A alone cannot
  see B's internals. *Mitigation:* run the guard in **each** repo (so B's own CI
  catches B→quantum), and/or aggregate edges across repos (roadmap item).
- **Dynamic import with a non-constant argument.** `import_module(name)` where
  `name` is computed at runtime is undecidable statically. *Mitigation:* lint/ban
  computed imports on the control path; runtime sandboxing.
- **Out-of-band execution.** `subprocess`, `exec`, `eval`, plugin/entry-point
  loading, RPC. These are runtime behavior, not imports.
- **Non-`.py` sources.** Cython/`.pyx`, generated code committed elsewhere,
  notebooks, native extensions, FFI.
- **Symlinks / submodules / vendored trees.** The guard scans files on disk; a
  git submodule or symlink can pull in code whose true origin differs from its path.
  *Mitigation:* scan submodules in their own repos; avoid layer dirs behind symlinks.
- **Root vs third-party name collision.** A layer root that equals a real PyPI
  package name can mis-map. *Mitigation:* use unambiguous root names; validation
  flags duplicates but not external collisions.
- **CI evasion (Wave 4).** An attacker with write access can delete the workflow,
  skip the check, or push to an unprotected branch. boundary-guard is a *check*,
  not access control. *Mitigation:* branch protection + **required** status check
  on the default branch, enforced by the org — outside this tool's scope.
