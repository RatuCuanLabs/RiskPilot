"""
Enums for the Minimal Risk Mitigation Engine.

Exactly the action/status literals from the spec, plus one honestly
necessary addition: NOT_NEEDED, for when current risk is already LOW
(or N/A) and there is nothing to mitigate. This is not a new business
rule or threshold — it is just the label for the "action = NONE, and
that's because things are already fine" case, distinct from
NO_EFFECTIVE_MITIGATION ("we tried, nothing helped").
"""

from enum import Enum


class MitigationAction(str, Enum):
    NONE = "NONE"
    REDUCE_POSITION = "REDUCE_POSITION"
    PARTIAL_CLOSE = "PARTIAL_CLOSE"
    HEDGE = "HEDGE"


class MitigationStatus(str, Enum):
    RECOMMENDED = "RECOMMENDED"
    NO_EFFECTIVE_MITIGATION = "NO_EFFECTIVE_MITIGATION"
    UNSUPPORTED = "UNSUPPORTED"
    NOT_NEEDED = "NOT_NEEDED"
