"""Red-team round 2 — discovery & honest documentation (no new features).

Two kinds of tests here:

  * Wave 2 (false positives): healthy code MUST produce zero findings.
  * Limitations (pinned): vectors the guard does NOT catch are asserted in their
    CURRENT (missed) state and labelled `test_LIMITATION_*`, so the gap is tracked
    and any future change is noticed. These mirror THREAT_MODEL.md — honest, not
    decorative.

Principle: a system that hasn't broken itself has no right to enforce on another.
"""

import tempfile
import textwrap
import unittest
from pathlib import Path

from boundary_guard import enforce
from boundary_guard.graph import ImportGraph
from boundary_guard.policy import Policy

POLICY = Policy.from_dsl(textwrap.dedent("""
    layer authgate         = authgate
    layer fdk              = fdk
    layer robotics         = robot
    layer quantum_research = quantum
    allow robotics -> fdk
    allow robotics -> authgate
    allow fdk      -> authgate
    forbid * -> quantum_research : research sandbox
"""))
LAYERS = POLICY.root_to_layer


def _tree(files):
    tmp = tempfile.mkdtemp()
    for rel, content in files.items():
        p = Path(tmp) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(content), encoding="utf-8")
    return tmp


def _check(files_or_roots, strict=False):
    roots = files_or_roots if isinstance(files_or_roots, list) else [_tree(files_or_roots)]
    g = ImportGraph.from_sources(roots, LAYERS)
    return enforce.check(g, POLICY, strict=strict)


def _hits_quantum(findings):
    return any(f.dst_layer == "quantum_research" for f in findings)


class TestWave2NoFalsePositives(unittest.TestCase):
    def test_reexport_chain_within_allowed_layers_is_clean(self):
        f = _check(
            {
                "robot/r.py": "import fdk\n",
                "fdk/__init__.py": "from authgate import thing\n",
                "authgate/__init__.py": "thing = 1\n",
            },
            strict=True,
        )
        self.assertEqual(f, [], f"false positive on a legitimate re-export chain: {f}")

    def test_conditional_runtime_import_of_allowed_layer_is_clean(self):
        f = _check({"robot/r.py": "def go():\n    import authgate\n    return authgate\n"}, strict=True)
        self.assertEqual(f, [])

    def test_try_except_import_of_allowed_layer_is_clean(self):
        f = _check({"robot/r.py": "try:\n    import authgate\nexcept ImportError:\n    authgate = None\n"}, strict=True)
        self.assertEqual(f, [])


class TestDecisions(unittest.TestCase):
    def test_DECISION_type_checking_import_is_flagged(self):
        # A TYPE_CHECKING-only import creates no runtime dependency, but it is still
        # architectural coupling. We flag it ON PURPOSE. Documented, not a bug.
        f = _check({"robot/r.py": "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import quantum\n"})
        self.assertTrue(_hits_quantum(f), "type-level coupling across a forbidden boundary should be flagged")


class TestLimitations(unittest.TestCase):
    """Each asserts a CURRENT miss. If one starts failing, the guard improved —
    update THREAT_MODEL.md accordingly."""

    def test_LIMITATION_cross_repo_transitive_when_only_one_repo_scanned(self):
        # robot imports a shared lib that lives in ANOTHER repo (not scanned here).
        repo_a = _tree({"robot/r.py": "import shared\n"})
        f = _check([repo_a], strict=True)
        self.assertFalse(_hits_quantum(f), "LIMITATION changed: cross-repo transitive now seen?")

    def test_cross_repo_transitive_IS_caught_when_aggregated(self):
        # Mitigation (existing capability, not a new feature): scan both repos.
        repo_a = _tree({"robot/r.py": "import shared\n"})
        repo_b = _tree({"shared/__init__.py": "import quantum\n"})  # unmapped -> (unscoped)
        f = _check([repo_a, repo_b], strict=True)
        self.assertTrue(_hits_quantum(f), "aggregated scan must catch the laundered transitive dep")

    def test_LIMITATION_nonconstant_dynamic_import_not_caught(self):
        f = _check({"robot/r.py": "import importlib\nn = 'quantum'\nimportlib.import_module(n)\n"})
        self.assertFalse(_hits_quantum(f), "LIMITATION changed: non-constant dynamic import now seen?")

    def test_LIMITATION_obfuscated_dunder_import_not_caught(self):
        f = _check({"robot/r.py": "import builtins\ngetattr(builtins, '__import__')('quantum')\n"})
        self.assertFalse(_hits_quantum(f), "LIMITATION changed: obfuscated __import__ now seen?")


if __name__ == "__main__":
    unittest.main()
