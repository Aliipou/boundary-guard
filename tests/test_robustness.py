import tempfile
import unittest
from pathlib import Path

from boundary_guard.graph import ImportGraph


class TestRobustness(unittest.TestCase):
    def test_syntax_error_is_skipped_not_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "a"
            pkg.mkdir()
            (pkg / "broken.py").write_text("def (:\n", encoding="utf-8")  # invalid syntax
            (pkg / "ok.py").write_text("import b\n", encoding="utf-8")
            g = ImportGraph.from_sources([tmp], {"a": "a", "b": "b"})
            # did not raise; still picked up the good edge
            self.assertIn(("a", "b"), g.layer_edges())

    def test_null_bytes_are_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "a"
            pkg.mkdir()
            (pkg / "weird.py").write_bytes(b"import b\x00\n")
            g = ImportGraph.from_sources([tmp], {"a": "a", "b": "b"})
            # must not crash; the null-byte file is simply ignored
            self.assertIsInstance(g.layer_edges(), set)

    def test_empty_tree_no_edges(self):
        with tempfile.TemporaryDirectory() as tmp:
            g = ImportGraph.from_sources([tmp], {"a": "a"})
            self.assertEqual(g.layer_edges(), set())

    def test_files_outside_known_layers_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            other = Path(tmp) / "unrelated"
            other.mkdir()
            (other / "m.py").write_text("import b\n", encoding="utf-8")
            g = ImportGraph.from_sources([tmp], {"a": "a", "b": "b"})
            self.assertEqual(g.layer_edges(), set())


if __name__ == "__main__":
    unittest.main()
