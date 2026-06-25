"""Component 3 — Enforcement.

Judges the graph against the policy and emits findings:

  - forbidden:  an edge the policy explicitly forbids (always a failure)
  - cycle:      a layer dependency cycle (always a failure)
  - undeclared: a cross-layer edge that is neither allowed nor forbidden
                (only reported in --strict mode; this is creeping drift)
"""

from __future__ import annotations

from dataclasses import dataclass

from .graph import ImportGraph
from .policy import Policy


@dataclass(frozen=True)
class Finding:
    kind: str
    src_layer: str
    dst_layer: str
    reason: str
    locations: tuple[str, ...] = ()


def check(graph: ImportGraph, policy: Policy, strict: bool = False) -> list[Finding]:
    locs: dict[tuple[str, str], list[str]] = {}
    for e in graph.edges:
        locs.setdefault((e.src_layer, e.dst_layer), []).append(
            f"{e.src_file}:{e.lineno} (import {e.module})"
        )

    findings: list[Finding] = []
    for (src, dst), locations in sorted(locs.items()):
        reason = policy.is_forbidden(src, dst)
        if reason is not None:
            findings.append(Finding("forbidden", src, dst, reason or "forbidden by policy", tuple(locations)))
        elif policy.is_allowed(src, dst):
            continue
        elif strict:
            findings.append(Finding(
                "undeclared", src, dst,
                "cross-layer dependency not declared in policy", tuple(locations),
            ))

    for cyc in graph.cycles():
        findings.append(Finding("cycle", cyc[0], cyc[-1], "layer cycle: " + " -> ".join(cyc)))

    return findings
