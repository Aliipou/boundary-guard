import tempfile
import unittest
from pathlib import Path

from boundary_guard import drift, profiles
from boundary_guard.graph import ImportEdge, ImportGraph
from boundary_guard.policy import Policy

ROOT = Path(__file__).resolve().parents[1]


class TestDrift(unittest.TestCase):
    def _graph(self, *edges):
        return ImportGraph([ImportEdge("f.py", 1, s, d, d) for s, d in edges])

    def test_no_drift_against_self(self):
        g = self._graph(("a", "b"), ("b", "c"))
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "b.json"
            drift.write_baseline(g, base)
            added, removed = drift.diff(base, g)
            self.assertEqual(added, [])
            self.assertEqual(removed, [])

    def test_new_edge_is_drift(self):
        old = self._graph(("a", "b"))
        new = self._graph(("a", "b"), ("a", "c"))
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "b.json"
            drift.write_baseline(old, base)
            added, removed = drift.diff(base, new)
            self.assertEqual(added, ["a -> c"])
            self.assertEqual(removed, [])


class TestProfiles(unittest.TestCase):
    def test_restrict_drops_invisible_layers(self):
        policy = Policy.from_file(ROOT / "policy.example.bgpolicy")
        restricted = profiles.restrict_policy(policy, ["robotics", "authgate", "quantum_research"])
        self.assertIn("robotics", restricted.layers)
        self.assertNotIn("banking", restricted.layers)
        # the robotics->quantum forbid survives projection
        self.assertIsNotNone(restricted.is_forbidden("robotics", "quantum_research"))
        # a forbid touching an invisible layer (authgate->banking) is dropped
        self.assertIsNone(restricted.is_forbidden("authgate", "banking"))


if __name__ == "__main__":
    unittest.main()
