"""
Candidate reduction quantity generation.

Deliberately simple: a small, fixed set of fractions of the current
position size, smallest first. This is NOT a Binance-specific formula
or a fitted/optimized set — it is a generic, deterministic sampling
strategy so the engine has a small number of candidates to test, per
the instruction to keep this simple and not build a full optimizer.
"""

from typing import List

# Ascending, so the engine can stop at the first candidate that works
# and know it is the smallest.
CANDIDATE_FRACTIONS = (0.1, 0.2, 0.4, 0.6, 0.8)


def generate_reduction_candidates(position_quantity: float) -> List[float]:
    if position_quantity is None or position_quantity <= 0:
        return []
    return [round(position_quantity * fraction, 10) for fraction in CANDIDATE_FRACTIONS]
