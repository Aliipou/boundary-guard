import unittest

from boundary_guard.policy import Policy

DSL = """
layer a = a, aa
layer b = b
layer q = quantum
allow b -> a
forbid a -> q : keep quantum out
forbid * -> b
"""


class TestPolicy(unittest.TestCase):
    def setUp(self):
        self.p = Policy.from_dsl(DSL)

    def test_layers_and_roots(self):
        self.assertEqual(self.p.layers["a"], ["a", "aa"])
        self.assertEqual(self.p.root_to_layer["aa"], "a")
        self.assertEqual(self.p.root_to_layer["quantum"], "q")

    def test_allow(self):
        self.assertTrue(self.p.is_allowed("b", "a"))
        self.assertFalse(self.p.is_allowed("a", "b"))

    def test_same_layer_always_allowed(self):
        self.assertTrue(self.p.is_allowed("a", "a"))

    def test_forbid_with_reason(self):
        self.assertEqual(self.p.is_forbidden("a", "q"), "keep quantum out")
        self.assertIsNone(self.p.is_forbidden("b", "a"))

    def test_wildcard_forbid(self):
        self.assertIsNotNone(self.p.is_forbidden("a", "b"))
        self.assertIsNotNone(self.p.is_forbidden("q", "b"))

    def test_forbid_beats_allow(self):
        # b -> a is allowed; add a wildcard forbid that also matches and ensure it wins.
        p = Policy.from_dsl(DSL + "\nforbid b -> a : override\n")
        self.assertIsNotNone(p.is_forbidden("b", "a"))


if __name__ == "__main__":
    unittest.main()
