"""
Deterministic, provider-agnostic simulation interface.

`MitigationSimulator` is a Protocol — an abstraction only. No formula is
implemented here. A real implementation (wired later, behind an AgentOS
adapter) would ask the exchange/account provider to project the effect
of a given reduction quantity and report back whatever it can. Any
field the provider cannot supply is left None — never guessed.

`risk_status` is the one field the candidate-selection logic in
engine.py actually depends on. If a provider cannot determine it for a
given candidate, it must return RiskStatus.UNKNOWN rather than a guess;
the engine treats UNKNOWN candidates as unverified, not as improvements.
"""

from dataclasses import dataclass
from typing import Optional, Protocol

from riskpilot.leverage.types import RiskStatus


@dataclass(frozen=True)
class ProjectedPositionState:
    quantity: float
    risk_status: RiskStatus
    notional_exposure: Optional[float] = None
    initial_margin: Optional[float] = None
    maintenance_margin: Optional[float] = None
    available_margin: Optional[float] = None


class MitigationSimulator(Protocol):
    def simulate(self, reduction_quantity: float) -> ProjectedPositionState:
        """
        Given a proposed reduction quantity, return the projected
        position/account state after applying it. Must not invent a
        risk_status it cannot determine — return RiskStatus.UNKNOWN
        instead.
        """
        ...
