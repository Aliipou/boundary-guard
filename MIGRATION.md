# Migration strategy — adopting boundary-guard in existing repos

Goal: enforce separation across `authgate-kernel`, `freedom-decision-kernel`,
`authrobo`, `banking`, `qfl` **without redesigning any of them**. Adoption is
additive and reversible. Nothing in the runtime changes.

## The master policy lives once

`policy.example.bgpolicy` is the single source of truth for layers and edges. It
belongs in this repo (or a shared `architecture/` repo). Every other repo
references a *profile* that projects it down.

## Per-repo adoption (3 files, ~20 minutes, zero code change)

For each repo, e.g. `authrobo`:

1. **Vendor the tool.** Copy the `boundary_guard/` package in (or `pip install`
   it from a git URL once published). It has no dependencies.
2. **Add a profile** — `boundaries/authrobo.profile.json`:
   ```json
   {"repo": "authrobo", "roots": ["src"],
    "visible_layers": ["robotics", "authgate", "fdk", "quantum_research"]}
   ```
   The repo only declares the layers it can actually produce edges to.
3. **Add the CI step:**
   ```yaml
   - run: python -m boundary_guard check --policy policy.bgpolicy --profile boundaries/authrobo.profile.json
   ```

## Rollout order (lowest risk first)

1. **Baseline, don't break.** In each repo run `baseline` to snapshot today's
   edges. Add a non-blocking `drift` job. This surfaces reality without failing
   anyone's build on day one.
2. **Turn on `forbidden`.** Enable `check` (forbidden + cycle only). These are
   true errors and should already be absent in healthy repos.
3. **Tighten to `--strict`.** Once `allow` edges are filled in to match reality,
   flip on `--strict` so *undeclared* cross-layer edges also fail. Now the
   architecture can't drift silently.

## What this deliberately does NOT do

- It does not move code, rename packages, or split modules.
- It does not touch import statements except to report on them.
- It does not run, mock, or depend on any guarded system.
- If a repo's real structure disagrees with the policy, the **policy** is edited
  to match reality first (via `graph`/`baseline`), then tightened — never the
  other way around in step one.
