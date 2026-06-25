"""Component 1 — Graph Engine.

Builds the cross-layer import graph from source, and answers structural questions
(layer edges, adjacency, cycles). It does not judge — `enforce` does that.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ImportEdge:
    src_file: str
    lineno: int
    src_layer: str
    dst_layer: str
    module: str


def _layer_of_path(path: Path, root_to_layer: dict[str, str]) -> str | None:
    for part in path.parts:
        if part in root_to_layer:
            return root_to_layer[part]
    return None


def _imported_roots(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split(".")[0], node.lineno
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative import -> same package, not a boundary crossing
                continue
            if node.module:
                yield node.module.split(".")[0], node.lineno


class ImportGraph:
    def __init__(self, edges: list[ImportEdge]):
        self.edges = list(edges)  # cross-layer edges only

    @classmethod
    def from_sources(cls, paths, root_to_layer: dict[str, str]) -> "ImportGraph":
        edges: list[ImportEdge] = []
        for root in paths:
            for py in sorted(Path(root).rglob("*.py")):
                src_layer = _layer_of_path(py, root_to_layer)
                if src_layer is None:
                    continue
                try:
                    tree = ast.parse(py.read_text(encoding="utf-8"))
                except SyntaxError:
                    continue
                for mod, lineno in _imported_roots(tree):
                    dst_layer = root_to_layer.get(mod)
                    if dst_layer is None or dst_layer == src_layer:
                        continue
                    edges.append(ImportEdge(str(py), lineno, src_layer, dst_layer, mod))
        return cls(edges)

    def layer_edges(self) -> set[tuple[str, str]]:
        return {(e.src_layer, e.dst_layer) for e in self.edges}

    def adjacency(self) -> dict[str, set[str]]:
        adj: dict[str, set[str]] = {}
        for s, d in self.layer_edges():
            adj.setdefault(s, set()).add(d)
        return adj

    def cycles(self) -> list[list[str]]:
        """Layer-level dependency cycles. A layered architecture must be acyclic."""
        adj = self.adjacency()
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {}
        stack: list[str] = []
        found: list[list[str]] = []

        def dfs(u: str) -> None:
            color[u] = GRAY
            stack.append(u)
            for v in sorted(adj.get(u, ())):
                c = color.get(v, WHITE)
                if c == GRAY:
                    found.append(stack[stack.index(v):] + [v])
                elif c == WHITE:
                    dfs(v)
            stack.pop()
            color[u] = BLACK

        for node in sorted(adj):
            if color.get(node, WHITE) == WHITE:
                dfs(node)
        return found
