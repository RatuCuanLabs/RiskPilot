"""
Phase 4 — Safe Mitigation Workflow Integration.

This module does not implement any new risk logic. It is a thin
orchestration wrapper that:
    1. Calls the existing, unmodified Phase 3 MitigationEngine.
    2. Maps the resulting action onto a Phase 2 TradeIntent using the
       existing, unmodified mitigation_action_to_trade_intent().
    3. Optionally re-checks that mapped intent against the existing,
       unmodified Phase 2 LeverageRiskEngine, purely for observability —
       to make it visible to a caller that the recommended action would
       (or would not) hit a Phase 2 hard block.

It never executes anything. `execution_performed` is hard-coded False
here — there is no code path in this module that can set it True. Any
actual execution still has to go through the existing, separate
confirmation/execution/verification pipeline untouched by this file.
"""

from dataclasses import dataclass
from typing import Optional

from riskpilot.leverage.types import RiskStatus, TradeIntent, MarketType
from riskpilot.leverage.snapshot import LeverageMarketSnapshot
from riskpilot.leverage.engine import LeverageRiskEngine
from riskpilot.mitigation.simulation import MitigationSimulator
from riskpilot.mitigation.engine import MitigationEngine, MitigationResult
from riskpilot.mitigation.integration import mitigation_action_to_trade_intent


@dataclass(frozen=True)
class MitigationWorkflowResult:
    mitigation: MitigationResult
    mapped_trade_intent: Optional[TradeIntent]
    would_be_hard_blocked: Optional[bool]  # None when not checked (no market context given, or no mapped intent)
    execution_performed: bool

    def as_dict(self) -> dict:
        d = dict(self.mitigation.as_dict()["mitigation"])
        d["mapped_trade_intent"] = self.mapped_trade_intent.value if self.mapped_trade_intent else None
        d["would_be_hard_blocked"] = self.would_be_hard_blocked
        d["execution_performed"] = self.execution_performed
        return d


def evaluate_mitigation_workflow(
    current_risk: RiskStatus,
    position_quantity: Optional[float],
    simulator: MitigationSimulator,
    market_type: Optional[MarketType] = None,
) -> MitigationWorkflowResult:
    """
    Runs the existing Phase 3 mitigation evaluation and, if a mitigation
    action was recommended, maps it to a Phase 2 TradeIntent. If a
    `market_type` is supplied, also re-checks that mapped intent through
    the existing, unmodified Phase 2 LeverageRiskEngine so the caller can
    see whether the recommended action would clear the Phase 2 hard-block
    gate — this is informational only and does not itself gate anything;
    the real gate is still the existing confirmation/safety pipeline.

    Never executes anything: `execution_performed` is always False.
    """
    mitigation_result = MitigationEngine.evaluate_reduction(current_risk, position_quantity, simulator)
    mapped_intent = mitigation_action_to_trade_intent(mitigation_result.recommended_action)

    would_be_hard_blocked: Optional[bool] = None
    if mapped_intent is not None and market_type is not None:
        snapshot = LeverageMarketSnapshot(market_type=market_type, current_risk_status=current_risk)
        leverage_check = LeverageRiskEngine.evaluate(snapshot, mapped_intent)
        would_be_hard_blocked = leverage_check.hard_block

    return MitigationWorkflowResult(
        mitigation=mitigation_result,
        mapped_trade_intent=mapped_intent,
        would_be_hard_blocked=would_be_hard_blocked,
        execution_performed=False,
    )
