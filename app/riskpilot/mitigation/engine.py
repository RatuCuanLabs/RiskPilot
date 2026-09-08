"""
Minimal Risk Mitigation Engine.

    "RiskPilot detects a dangerous leveraged position, simulates simple
    risk-reducing position reductions, and recommends the SMALLEST
    effective reduction that improves the risk state."

This is a proposal engine only: DETECT -> SIMULATE -> RECOMMEND. It
never executes anything, and it never invents a risk formula, threshold,
or exposure limit — risk classification for each candidate comes from
the caller-supplied MitigationSimulator, exactly as the Leverage Risk
Engine (Phase 2) takes its classification from an external provider
rather than computing it from raw margin numbers itself.

Risk ordering (severity, low to high) is just an ordinal ranking of the
already-named RiskStatus categories — not a new numeric threshold:
    LOW < WARNING < CRITICAL
UNKNOWN and NOT_APPLICABLE are excluded from the ordering: an
unverifiable candidate is never treated as an improvement.
"""

from dataclasses import dataclass
from typing import Optional

from riskpilot.leverage.types import RiskStatus
from .types import MitigationAction, MitigationStatus
from .candidates import generate_reduction_candidates
from .simulation import MitigationSimulator

_RISK_SEVERITY = {
    RiskStatus.LOW: 0,
    RiskStatus.WARNING: 1,
    RiskStatus.CRITICAL: 2,
}

_NO_MITIGATION_NEEDED = (RiskStatus.LOW, RiskStatus.NOT_APPLICABLE)


@dataclass(frozen=True)
class MitigationResult:
    status: MitigationStatus
    recommended_action: MitigationAction
    current_risk: RiskStatus
    quantity: Optional[float] = None
    projected_risk: Optional[RiskStatus] = None

    def as_dict(self) -> dict:
        return {
            "mitigation": {
                "status": self.status.value,
                "recommended_action": self.recommended_action.value,
                "quantity": self.quantity,
                "current_risk": self.current_risk.value,
                "projected_risk": self.projected_risk.value if self.projected_risk else None,
            }
        }

    def render_proposal(self, symbol: str = "") -> str:
        if self.status == MitigationStatus.NOT_NEEDED:
            return f"Current risk is {self.current_risk.value}. No mitigation needed."
        if self.status == MitigationStatus.NO_EFFECTIVE_MITIGATION:
            return (
                f"Current risk is {self.current_risk.value}. No simulated reduction "
                f"among the candidates tested improved the risk state."
            )
        if self.status == MitigationStatus.UNSUPPORTED:
            return (
                "A hedge was considered, but there is no deterministic evidence it "
                "would improve the risk state. Not recommended."
            )
        label = symbol + " " if symbol else ""
        return (
            "Risk Mitigation Proposal\n\n"
            f"Current Risk: {self.current_risk.value}\n"
            f"Recommended Action: {self.recommended_action.value.replace('_', ' ').title()}\n"
            f"Proposed Reduction: {self.quantity} {label}\n"
            f"Expected Risk: {self.current_risk.value} -> {self.projected_risk.value}\n\n"
            "This is a proposal only — it will not be executed automatically.\n"
            "Confirm mitigation?"
        )


class MitigationEngine:

    @staticmethod
    def evaluate_reduction(
        current_risk: RiskStatus,
        position_quantity: Optional[float],
        simulator: MitigationSimulator,
    ) -> MitigationResult:
        if current_risk in _NO_MITIGATION_NEEDED:
            return MitigationResult(
                status=MitigationStatus.NOT_NEEDED,
                recommended_action=MitigationAction.NONE,
                current_risk=current_risk,
            )

        if current_risk == RiskStatus.UNKNOWN:
            # We cannot verify an improvement over a baseline we can't
            # classify, and we must not guess. Report honestly.
            return MitigationResult(
                status=MitigationStatus.NO_EFFECTIVE_MITIGATION,
                recommended_action=MitigationAction.NONE,
                current_risk=current_risk,
            )

        candidates = generate_reduction_candidates(position_quantity)
        if not candidates:
            return MitigationResult(
                status=MitigationStatus.NO_EFFECTIVE_MITIGATION,
                recommended_action=MitigationAction.NONE,
                current_risk=current_risk,
            )

        current_severity = _RISK_SEVERITY[current_risk]

        for qty in candidates:  # ascending order -> first hit is the smallest effective one
            projected = simulator.simulate(qty)
            projected_status = projected.risk_status
            if projected_status not in _RISK_SEVERITY:
                continue  # UNKNOWN/NOT_APPLICABLE can't be counted as an improvement
            if _RISK_SEVERITY[projected_status] < current_severity:
                return MitigationResult(
                    status=MitigationStatus.RECOMMENDED,
                    recommended_action=MitigationAction.PARTIAL_CLOSE,
                    current_risk=current_risk,
                    quantity=qty,
                    projected_risk=projected_status,
                )

        return MitigationResult(
            status=MitigationStatus.NO_EFFECTIVE_MITIGATION,
            recommended_action=MitigationAction.NONE,
            current_risk=current_risk,
        )

    @staticmethod
    def evaluate_hedge(current_risk: RiskStatus) -> MitigationResult:
        # No deterministic hedge-improvement simulation exists in this
        # phase. A hedge is NEVER assumed to be safer.
        return MitigationResult(
            status=MitigationStatus.UNSUPPORTED,
            recommended_action=MitigationAction.HEDGE,
            current_risk=current_risk,
        )
