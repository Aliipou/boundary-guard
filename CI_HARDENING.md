# CI hardening — closing CI evasion (Wave 4)

> Low-claim and honest: this adds **no runtime code and no feature**. It documents
> the GitHub configuration that turns the boundary check from "a tool you can skip"
> into "a gate you cannot merge around." boundary-guard cannot enforce any of this
> itself — it is repo/org configuration, and an org admin can always change it.

## Threat model (what we must make impossible, not just unlikely)

| | Evasion | Closed by |
|---|---------|-----------|
| **A** | direct commit to the default branch; force-push; branch deletion | branch protection: require PR, `allow_force_pushes=false`, `allow_deletions=false` |
| **B** | delete the workflow file / rename its path / disable Actions | make the check a **required status check** — a required context that never reports **blocks merge**, so deleting the workflow blocks the PR instead of passing it |
| **C** | the check exists but isn't *required* (silent, advisory) | mark the exact check contexts as required; `enforce_admins=true` |
| **D** | "fake green": a job that exits 0 without running enforcement | the job must run the real `boundary_guard check --strict`; pin action versions; lock workflow edits behind review (CODEOWNERS) so a no-op rewrite needs approval |

## Required configuration (per repo)

Mental model: **CI is part of the security boundary, not a convenience.** Apply
branch protection to the default branch with these settings:

```bash
REPO=Aliipou/boundary-guard
BRANCH=master            # authrobo etc. use: main

gh api -X PUT "repos/$REPO/branches/$BRANCH/protection" --input - <<'JSON'
{
  "required_status_checks": { "strict": true, "contexts": ["test", "self-enforce"] },
  "enforce_admins": true,
  "required_pull_request_reviews": { "required_approving_review_count": 1, "dismiss_stale_reviews": true },
  "restrictions": null,
  "required_conversation_resolution": true,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
```

For a repo that runs the boundaries check (e.g. authrobo), set
`"contexts": ["enforce-boundaries"]` to match that workflow's job name.

### Workflow tamper lock

Add `CODEOWNERS` so any change to the workflow, the policy, or the guard itself
requires the owner's review (defeats "rewrite the workflow into a no-op"):

```
/.github/                 @Aliipou
/policy.example.bgpolicy   @Aliipou
/boundary_guard/           @Aliipou
```

…and in branch protection, require review (above) — CODEOWNERS only bites when
reviews are required.

## Honest caveats (what this does NOT achieve)

- **Org admin can still change settings.** `enforce_admins=true` covers merges,
  not settings edits. Branch protection is only as strong as who can edit it.
- **Required checks need the check to actually run.** On a **private** repo whose
  Actions are blocked (e.g. a billing/spending-limit issue), a required check can
  never report → **every** PR is blocked. So do **not** enable required checks on
  boundary-guard until its Actions can run; enable on public repos (authrobo) now.
- **This is config, not a guarantee.** It raises the cost of evasion to "change
  org policy," which is the right bar — but it is not cryptographic enforcement.

## Status

Not auto-applied. boundary-guard is private with Actions currently blocked, so
enabling a required check now would self-DoS merges. Run the script above per repo
once Actions can run (public repos immediately; boundary-guard after billing).
