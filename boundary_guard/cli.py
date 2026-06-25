"""Command-line interface — the surface CI calls.

    python -m boundary_guard check  <paths...> --policy P [--profile F] [--strict]
    python -m boundary_guard graph  <paths...> --policy P
    python -m boundary_guard baseline <paths...> --policy P --out baseline.json
    python -m boundary_guard drift  <paths...> --policy P --baseline baseline.json
    python -m boundary_guard viz    --policy P [--format mermaid|dot]
"""

from __future__ import annotations

import argparse
import sys

from . import drift as drift_mod
from . import enforce, profiles, viz
from .graph import ImportGraph
from .policy import Policy


def _resolve(args):
    policy = Policy.from_file(args.policy)
    paths = args.paths
    if getattr(args, "profile", None):
        prof = profiles.Profile.from_file(args.profile)
        policy = profiles.restrict_policy(policy, prof.visible_layers)
        paths = prof.roots
    return policy, paths


def cmd_check(args) -> int:
    policy, paths = _resolve(args)
    graph = ImportGraph.from_sources(paths, policy.root_to_layer)
    findings = enforce.check(graph, policy, strict=args.strict)
    if not findings:
        print(f"OK — boundaries hold under {', '.join(paths)}")
        return 0
    print(f"BOUNDARY FINDINGS ({len(findings)}):\n")
    for f in findings:
        print(f"  [{f.kind}] {f.src_layer} -> {f.dst_layer}")
        print(f"      {f.reason}")
        for loc in f.locations:
            print(f"        at {loc}")
        print()
    return 1


def cmd_graph(args) -> int:
    policy, paths = _resolve(args)
    graph = ImportGraph.from_sources(paths, policy.root_to_layer)
    for s, d in sorted(graph.layer_edges()):
        print(f"{s} -> {d}")
    return 0


def cmd_baseline(args) -> int:
    policy, paths = _resolve(args)
    graph = ImportGraph.from_sources(paths, policy.root_to_layer)
    drift_mod.write_baseline(graph, args.out)
    print(f"baseline written to {args.out} ({len(graph.layer_edges())} edges)")
    return 0


def cmd_drift(args) -> int:
    policy, paths = _resolve(args)
    graph = ImportGraph.from_sources(paths, policy.root_to_layer)
    added, removed = drift_mod.diff(args.baseline, graph)
    for e in added:
        print(f"+ {e}   (new cross-layer dependency)")
    for e in removed:
        print(f"- {e}   (dependency removed)")
    if not added and not removed:
        print("no drift — graph matches baseline")
        return 0
    return 1 if added else 0


def cmd_viz(args) -> int:
    policy = Policy.from_file(args.policy)
    print(viz.to_dot(policy) if args.format == "dot" else viz.to_mermaid(policy))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="boundary_guard")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp, with_paths=True):
        if with_paths:
            sp.add_argument("paths", nargs="*", default=["."])
        sp.add_argument("--policy", required=True)
        sp.add_argument("--profile")

    c = sub.add_parser("check"); add_common(c); c.add_argument("--strict", action="store_true"); c.set_defaults(func=cmd_check)
    g = sub.add_parser("graph"); add_common(g); g.set_defaults(func=cmd_graph)
    b = sub.add_parser("baseline"); add_common(b); b.add_argument("--out", default="boundaries.baseline.json"); b.set_defaults(func=cmd_baseline)
    d = sub.add_parser("drift"); add_common(d); d.add_argument("--baseline", default="boundaries.baseline.json"); d.set_defaults(func=cmd_drift)
    v = sub.add_parser("viz"); v.add_argument("--policy", required=True); v.add_argument("--format", choices=["mermaid", "dot"], default="mermaid"); v.set_defaults(func=cmd_viz, paths=[], profile=None)
    return p


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    return args.func(args)
