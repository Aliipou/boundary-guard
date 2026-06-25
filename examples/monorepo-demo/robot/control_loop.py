"""Robotics control loop (layer: robotics).

Deliberately violates the policy to prove the guard catches it: a safety-critical
control path must never reach into quantum research.
"""

import quantum.qkd  # <-- FORBIDDEN: no quantum on a real-time safety path


def step():
    return quantum.qkd.sample()
