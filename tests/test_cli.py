import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from boundary_guard import cli

ROOT = Path(__file__).resolve().parents[1]
POLICY = str(ROOT / "policy.example.bgpolicy")
DEMO = str(ROOT / "examples" / "monorepo-demo")
DEMO_FDK = str(ROOT / "examples" / "monorepo-demo" / "fdk")


def run(argv):
    """Run the CLI, capturing stdout; return (exit_code, output)."""
    out = io.StringIO()
    code = 0
    try:
        with redirect_stdout(out), redirect_stderr(out):
            code = cli.main(argv)
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
    return code, out.getvalue()


class TestCli(unittest.TestCase):
    def test_check_violation_exits_1(self):
        code, out = run(["check", DEMO, "--policy", POLICY])
        self.assertEqual(code, 1)
        self.assertIn("robotics -> quantum_research", out)

    def test_check_clean_exits_0(self):
        code, out = run(["check", DEMO_FDK, "--policy", POLICY])
        self.assertEqual(code, 0)
        self.assertIn("OK", out)

    def test_graph_exits_0(self):
        code, out = run(["graph", DEMO, "--policy", POLICY])
        self.assertEqual(code, 0)
        self.assertIn("fdk -> authgate", out)

    def test_viz_exits_0(self):
        code, out = run(["viz", "--policy", POLICY])
        self.assertEqual(code, 0)
        self.assertIn("flowchart", out)

    def test_invalid_policy_exits_2(self):
        bad = ROOT / "tests" / "_bad.bgpolicy"
        bad.write_text("layer a = a\nallow a -> ghost\n", encoding="utf-8")
        try:
            code, out = run(["check", DEMO, "--policy", str(bad)])
        finally:
            bad.unlink()
        self.assertEqual(code, 2)
        self.assertIn("INVALID POLICY", out)

    def test_missing_path_exits_2(self):
        code, out = run(["check", "no_such_dir_xyz", "--policy", POLICY])
        self.assertEqual(code, 2)
        self.assertIn("not found", out)

    def test_version(self):
        code, out = run(["--version"])
        self.assertEqual(code, 0)
        self.assertIn("boundary-guard", out)

    def test_profile_scoped_check(self):
        prof = str(ROOT / "profiles" / "authrobo.profile.json")
        # profile roots are ["."]; run from repo root so it resolves
        import os
        cwd = os.getcwd()
        os.chdir(ROOT)
        try:
            code, out = run(["check", "--policy", POLICY, "--profile", prof])
        finally:
            os.chdir(cwd)
        self.assertEqual(code, 1)
        self.assertIn("robotics -> quantum_research", out)


if __name__ == "__main__":
    unittest.main()
