import unittest
from pathlib import Path

from boundary_guard.graph import ImportEdge, ImportGraph
from boundary_guard.policy import Policy

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "monorepo-demo"


class TestGraph(unittest.TestCase):
    def test_build_from_sources(self):
        policy = Policy.from_file(ROOT / "policy.example.bgpolicy")
        g = ImportGraph.from_sources([str(DEMO)], policy.root_to_layer)
        edges = g.layer_edges()
        self.assertIn(("robotics", "quantum_research"), edges)
        self.assertIn(("fdk", "authgate"), edges)

    def test_relative_imports_ignored(self):
        # same-layer / relative imports must not appear as cross-layer edges
        policy = Policy.from_file(ROOT / "policy.example.bgpolicy")
        g = ImportGraph.from_sources([str(DEMO)], policy.root_to_layer)
        self.assertNotIn(("authgate", "authgate"), g.layer_edges())

    def test_cycle_detection(self):
        edges = [
            ImportEdge("x.py", 1, "a", "b", "b"),
            ImportEdge("y.py", 1, "b", "a", "a"),
        ]
        g = ImportGraph(edges)
        self.assertTrue(g.cycles())

    def test_no_false_cycle(self):
        edges = [
            ImportEdge("x.py", 1, "a", "b", "b"),
            ImportEdge("y.py", 1, "b", "c", "c"),
        ]
        g = ImportGraph(edges)
        self.assertEqual(g.cycles(), [])


if __name__ == "__main__":
    unittest.main()
