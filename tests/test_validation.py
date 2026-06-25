import unittest

from boundary_guard.policy import Policy


class TestValidation(unittest.TestCase):
    def test_valid_policy_has_no_errors(self):
        p = Policy.from_dsl("layer a = a\nlayer b = b\nallow b -> a\nforbid a -> b\n")
        self.assertEqual(p.validate(), [])

    def test_unknown_layer_in_allow(self):
        p = Policy.from_dsl("layer a = a\nallow a -> typo\n")
        self.assertTrue(any("undeclared" in e for e in p.validate()))

    def test_unknown_layer_in_forbid(self):
        p = Policy.from_dsl("layer a = a\nforbid nope -> a\n")
        self.assertTrue(any("undeclared" in e for e in p.validate()))

    def test_duplicate_root_across_layers(self):
        p = Policy.from_dsl("layer a = shared\nlayer b = shared\n")
        self.assertTrue(any("claimed by both" in e for e in p.validate()))

    def test_empty_layer(self):
        p = Policy.from_dsl("layer a =\nlayer b = b\n")
        self.assertTrue(any("no import roots" in e for e in p.validate()))

    def test_wildcards_are_not_undeclared(self):
        p = Policy.from_dsl("layer a = a\nallow a -> *\nforbid * -> a\n")
        self.assertEqual(p.validate(), [])

    def test_example_policies_are_valid(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        for name in ("policy.example.bgpolicy", "policy.example.json"):
            with self.subTest(policy=name):
                self.assertEqual(Policy.from_file(root / name).validate(), [])

    def test_bad_dsl_line_raises(self):
        with self.assertRaises(ValueError):
            Policy.from_dsl("this is not valid\n")


if __name__ == "__main__":
    unittest.main()
