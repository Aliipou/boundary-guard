"""Hostile-reviewer suite. Each test asserts the SECURE behavior an attacker
should not be able to defeat. A failing test here = a real, demonstrated bypass.

Threat: a developer (or a prompt-injected agent) tries to make a forbidden
cross-layer dependency exist while keeping boundary-guard green.
"""

import tempfile
import textwrap
import unittest
from pathlib import Path

from boundary_guard import enforce
from boundary_guard.graph import ImportGraph
from boundary_guard.policy import Policy

ROOT = Path(__file__).resolve().parents[1]

# Minimal policy: nothing anywhere may import the quantum_research sandbox.
POLICY = Policy.from_dsl(textwrap.dedent("""
    layer robotics         = robot
    layer quantum_research = quantum
    forbid * -> quantum_research : research sandbox; nothing in production imports it
"""))


def _tree(files: dict[str, str]) -> str:
    tmp = tempfile.mkdtemp()
    for rel, content in files.items():
        p = Path(tmp) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(content), encoding="utf-8")
    return tmp


def _check(files, strict=False):
    g = ImportGraph.from_sources([_tree(files)], POLICY.root_to_layer)
    return enforce.check(g, POLICY, strict=strict)


def _hits_quantum(findings):
    return any(f.dst_layer == "quantum_research" for f in findings)


class TestAdversarial(unittest.TestCase):
    # --- evasion via dynamic imports (the import is invisible to a naive AST walk) ---
    def test_dynamic_importlib_is_caught(self):
        f = _check({"robot/x.py": 'import importlib\nimportlib.import_module("quantum")\n'})
        self.assertTrue(_hits_quantum(f), "BYPASS: importlib.import_module hides the forbidden dep")

    def test_dunder_import_is_caught(self):
        f = _check({"robot/x.py": '__import__("quantum")\n'})
        self.assertTrue(_hits_quantum(f), "BYPASS: __import__ hides the forbidden dep")

    def test_from_importlib_aliased_is_caught(self):
        f = _check({"robot/x.py": 'from importlib import import_module as im\nim("quantum")\n'})
        self.assertTrue(_hits_quantum(f), "BYPASS: aliased import_module hides the forbidden dep")

    # --- laundering through a module that lives outside any declared layer ---
    def test_launder_through_unmapped_module_is_caught(self):
        f = _check(
            {
                "robot/x.py": "import shared.helper\n",
                "shared/helper.py": "import quantum\n",
            },
            strict=True,
        )
        self.assertTrue(_hits_quantum(f), "BYPASS: forbidden dep laundered through an unmapped 'shared/' module")

    # --- a file the parser can't read must not become a silent blind spot ---
    def test_unparseable_file_is_surfaced(self):
        f = _check({"robot/bad.py": "import quantum\ndef (:\n"}, strict=True)
        self.assertTrue(
            any(x.kind in ("unanalyzable", "forbidden") for x in f),
            "BYPASS: an unparseable file is silently skipped, hiding its imports",
        )

    # --- policy completeness: spoofing into a layer that lacks an explicit forbid ---
    def test_example_policy_blocks_quantum_from_every_layer(self):
        p = Policy.from_file(ROOT / "policy.example.bgpolicy")
        for layer in ("observability", "banking", "robotics", "authgate", "fdk", "philosophy"):
            with self.subTest(layer=layer):
                self.assertIsNotNone(
                    p.is_forbidden(layer, "quantum_research"),
                    f"SPOOFABLE: code placed in a '{layer}'-named dir can import quantum",
                )


if __name__ == "__main__":
    unittest.main()
