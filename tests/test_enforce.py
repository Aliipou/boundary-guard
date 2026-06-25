import unittest
from pathlib import Path

from boundary_guard import enforce
from boundary_guard.graph import ImportEdge, ImportGraph
from boundary_guard.policy import Policy

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "monorepo-demo"


class TestEnforce(unittest.TestCase):
    def setUp(self):
        self.policy = Policy.from_file(ROOT / "policy.example.bgpolicy")
        self.graph = ImportGraph.from_sources([str(DEMO)], self.policy.root_to_layer)

    def test_catches_forbidden(self):
        findings = enforce.check(self.graph, self.policy)
        pairs = {(f.src_layer, f.dst_layer, f.kind) for f in findings}
        self.assertIn(("robotics", "quantum_research", "forbidden"), pairs)

    def test_allows_declared_edge(self):
        findings = enforce.check(self.graph, self.policy)
        self.assertNotIn(("fdk", "authgate"), {(f.src_layer, f.dst_layer) for f in findings})

    def test_demo_is_clean_except_violation(self):
        findings = enforce.check(self.graph, self.policy, strict=True)
        self.assertEqual(len(findings), 1)

    def test_undeclared_only_in_strict(self):
        policy = Policy.from_dsl("layer a = a\nlayer b = b\n")  # no allow/forbid
        graph = ImportGraph([ImportEdge("x.py", 1, "a", "b", "b")])
        self.assertEqual(enforce.check(graph, policy, strict=False), [])
        strict = enforce.check(graph, policy, strict=True)
        self.assertEqual(len(strict), 1)
        self.assertEqual(strict[0].kind, "undeclared")

    def test_cycle_is_a_finding(self):
        policy = Policy.from_dsl("layer a = a\nlayer b = b\nallow a -> b\nallow b -> a\n")
        graph = ImportGraph([
            ImportEdge("x.py", 1, "a", "b", "b"),
            ImportEdge("y.py", 1, "b", "a", "a"),
        ])
        kinds = {f.kind for f in enforce.check(graph, policy)}
        self.assertIn("cycle", kinds)


if __name__ == "__main__":
    unittest.main()
