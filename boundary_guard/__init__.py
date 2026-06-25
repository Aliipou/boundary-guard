"""boundary-guard — architecture-boundary enforcement for separate repositories.

A dev-time framework. It never imports, wraps, or runs the systems it guards;
it only reads their source and enforces separation. Stdlib only, no runtime deps.
"""

from .policy import Policy
from .graph import ImportGraph, ImportEdge
from .enforce import Finding, check
from .profiles import Profile, restrict_policy

__all__ = [
    "Policy",
    "ImportGraph",
    "ImportEdge",
    "Finding",
    "check",
    "Profile",
    "restrict_policy",
]
