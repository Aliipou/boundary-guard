"""Red-team waves 1-5 beyond the first bypass set.

Wave 1: more evasion (policy shadowing, wildcard abuse, indirect-through-layer).
Wave 2: false positives must be ~0 on healthy code.
Wave 3: transitive coupling is caught *within* a repo (cross-repo is a documented
        limitation, see THREAT_MODEL.md).
Wave 5: scale — stays fast and deterministic on a large tree.
"""

import tempfile
import textwrap
import time
import unittest
from pathlib import Path

from boundary_guard import enforce
from boundary_guard.graph import ImportGraph
from boundary_guard.policy import Policy

POLICY = Policy.from_dsl(textwrap.dedent("""
    layer authgate         = authgate
    layer fdk              = fdk
    layer banking          = banking
    layer robotics         = robot
    layer quantum_research = quantum
    allow fdk      -> authgate
    allow banking  -> authgate
    allow robotics -> authgate
    allow robotics -> fdk
    forbid * -> quantum_research : research sandbox
    forbid authgate -> banking   : kernel holds no money state
"""))
LAYERS = POLICY.root_to_layer


def _tree(files):
    tmp = tempfile.mkdtemp()
    for rel, content in files.items():
        p = Path(tmp) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(content), encoding="utf-8")
    return tmp


def _check(files, strict=False, policy=POLICY):
    g = ImportGraph.from_sources([_tree(files)], policy.root_to_layer)
    return enforce.check(g, policy, strict=strict)


class TestWave1Evasion(unittest.TestCase):
    def test_wildcard_allow_all_is_rejected_by_validation(self):
        p = Policy.from_dsl("layer a = a\nlayer b = b\nallow * -> *\n")
        self.assertTrue(any("disables" in e for e in p.validate()))

    def test_forbid_beats_a_shadowing_allow(self):
        p = Policy.from_dsl(
            "layer a = a\nlayer q = quantum\nallow a -> q\nforbid a -> q : no\n"
        )
        f = _check({"a/x.py": "import quantum\n"}, policy=p)
        self.assertTrue(any(x.kind == "forbidden" for x in f), "a shadowing allow defeated the forbid")

    def test_indirect_through_a_layer_is_still_visible(self):
        # authgate -> banking is forbidden directly. Even if authgate only *means*
        # to reach banking, the authgate->banking edge is flagged.
        f = _check({"authgate/x.py": "import banking\n"})
        self.assertTrue(any((x.src_layer, x.dst_layer) == ("authgate", "banking") for x in f))


class TestWave2FalsePositives(unittest.TestCase):
    def test_deep_nested_allowed_import_is_clean(self):
        f = _check({"robot/a/b/c/deep.py": "import authgate\n"})
        self.assertEqual(f, [], f"false positive on a legitimate robotics->authgate: {f}")

    def test_full_allowed_chain_is_clean(self):
        f = _check(
            {
                "robot/r.py": "import authgate\nimport fdk\n",
                "fdk/f.py": "import authgate\n",
                "banking/b.py": "import authgate\n",
            },
            strict=True,
        )
        self.assertEqual(f, [], f"false positives on a healthy graph: {f}")

    def test_stdlib_and_thirdparty_imports_are_ignored(self):
        f = _check({"robot/r.py": "import os, sys, json\nimport numpy\n"}, strict=True)
        self.assertEqual(f, [])


class TestWave3Transitive(unittest.TestCase):
    def test_transitive_within_repo_is_caught_at_each_edge(self):
        # robot -> midlayer(fdk) allowed, but fdk -> quantum is forbidden: the
        # forbidden hop surfaces even though robot never names quantum.
        f = _check(
            {
                "robot/r.py": "import fdk\n",
                "fdk/f.py": "import quantum\n",
            }
        )
        self.assertTrue(any((x.src_layer, x.dst_layer) == ("fdk", "quantum_research") for x in f))


class TestWave5Scale(unittest.TestCase):
    def test_large_tree_is_fast_and_deterministic(self):
        files = {}
        for i in range(250):
            files[f"robot/m{i}.py"] = "import authgate\n"      # allowed
        files["robot/bad.py"] = "import quantum\n"             # one violation
        tmp = _tree(files)

        t0 = time.perf_counter()
        g1 = ImportGraph.from_sources([tmp], LAYERS)
        f1 = enforce.check(g1, POLICY, strict=True)
        elapsed = time.perf_counter() - t0

        f2 = enforce.check(ImportGraph.from_sources([tmp], LAYERS), POLICY, strict=True)

        self.assertLess(elapsed, 5.0, "scale: 250+ files took too long")
        forbidden = [x for x in f1 if x.kind == "forbidden"]
        self.assertEqual(len(forbidden), 1)
        self.assertEqual([(x.kind, x.src_layer, x.dst_layer) for x in f1],
                         [(x.kind, x.src_layer, x.dst_layer) for x in f2],
                         "non-deterministic output")


if __name__ == "__main__":
    unittest.main()
