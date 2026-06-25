"""Self-test: the guard must flag the forbidden edge and stay silent on the allowed one.

    python selftest.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import boundary_guard as bg

ROOT = Path(__file__).resolve().parent
POLICY = ROOT / "policy.example.json"
DEMO = ROOT / "examples" / "monorepo-demo"


def main() -> int:
    violations = bg.check([str(DEMO)], str(POLICY))
    by_pair = {(v[2], v[3]) for v in violations}

    failures = []
    # Must catch robotics -> quantum_research.
    if ("robotics", "quantum_research") not in by_pair:
        failures.append("expected a robotics -> quantum_research violation, none found")
    # Must NOT flag the allowed fdk -> authgate crossing.
    if ("fdk", "authgate") in by_pair:
        failures.append("fdk -> authgate is allowed but was flagged")
    # Exactly one violation in this demo.
    if len(violations) != 1:
        failures.append(f"expected exactly 1 violation, got {len(violations)}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS — guard caught the forbidden edge and left the allowed one alone")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
