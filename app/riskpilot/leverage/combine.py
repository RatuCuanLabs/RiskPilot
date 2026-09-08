"""
Combines the (momentum-based) Decision Engine result with the Leverage
Risk Engine result into one final verdict.

This is where "momentum can never override a CRITICAL or UNKNOWN
leveraged safety block" is actually enforced in code, rather than left
as a prose promise: `hard_block` from the leverage engine is checked
FIRST and unconditionally overrides whatever the Decision Engine
concluded from momentum/portfolio risk. There is no code path in this
function where a leverage hard_block can be bypassed by any decision
value, including "EXECUTE" from PLATINUM momentum.
"""

from dataclasses import dataclass

from riskpilot.decision.engine import DecisionResult
from riskpilot.leverage.engine import LeverageRiskResult

HARD_BLOCK = "HARD BLOCK"


@dataclass(frozen=True)
class FinalTradeVerdict:
    final_action: str  # one of: "EXECUTE", "BUY WITH NOTE", "WAIT/HOLD", "HARD BLOCK"
    decision: str  # the raw Decision Engine output, preserved for transparency
    leverage_risk_status: str
    hard_block: bool
    override_allowed: bool
    reason: str

    def as_dict(self) -> dict:
        return {
            "final_action": self.final_action,
            "decision": self.decision,
            "leverage_risk_status": self.leverage_risk_status,
            "hard_block": self.hard_block,
            "override_allowed": self.override_allowed,
            "reason": self.reason,
        }


def combine_decision_with_leverage_risk(
    decision_result: DecisionResult,
    leverage_result: LeverageRiskResult,
) -> FinalTradeVerdict:
    if leverage_result.hard_block:
        return FinalTradeVerdict(
            final_action=HARD_BLOCK,
            decision=decision_result.decision,
            leverage_risk_status=leverage_result.risk_status.value,
            hard_block=True,
            override_allowed=False,
            reason=(
                f"Leverage/liquidation risk is {leverage_result.risk_status.value} "
                f"for intent={leverage_result.intent.value}, which is a hard, "
                f"non-overridable block. This overrides the momentum-based decision "
                f"of {decision_result.decision} ({decision_result.momentum} "
                f"{decision_result.score}/4) — momentum can never override a "
                f"CRITICAL or UNKNOWN leveraged safety block."
            ),
        )

    return FinalTradeVerdict(
        final_action=decision_result.decision,
        decision=decision_result.decision,
        leverage_risk_status=leverage_result.risk_status.value,
        hard_block=False,
        override_allowed=leverage_result.override_allowed,
        reason=(
            f"No leverage hard block (leverage risk: {leverage_result.risk_status.value}); "
            f"momentum-based decision stands: {decision_result.reason}"
        ),
    )
