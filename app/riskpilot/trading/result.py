"""
Structured trade analysis result.

Assembles a plain, JSON-serializable result from already-computed
engine outputs (Momentum, Decision, HardSafety). It performs no
calculation of its own and never invents a field it cannot honestly
populate — e.g. request_id is a plain generated identifier, not a
business fact.
"""

import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class TradeAnalysisResult:
    symbol: str
    market: str
    action: str
    momentum_score: int
    momentum_total: int
    momentum_level: str
    portfolio_risk_status: str
    decision_status: str
    hard_block: bool
    override_allowed: bool
    confirmation_required: bool
    confirmation_type: Optional[str]
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def as_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "symbol": self.symbol,
            "market": self.market,
            "action": self.action,
            "momentum": {
                "score": self.momentum_score,
                "total": self.momentum_total,
                "level": self.momentum_level,
            },
            "portfolio_risk": {"status": self.portfolio_risk_status},
            "decision": {
                "status": self.decision_status,
                "hard_block": self.hard_block,
                "override_allowed": self.override_allowed,
            },
            "confirmation": {
                "required": self.confirmation_required,
                "type": self.confirmation_type,
            },
        }


def build_trade_analysis_result(
    symbol: str,
    momentum_score: int,
    momentum_level: str,
    portfolio_risk_status: str,
    decision_status: str,
    decision_actionable: bool,
    hard_block: bool,
    market: str = "SPOT",
    action: str = "OPEN",
) -> TradeAnalysisResult:
    override_allowed = not hard_block

    if hard_block:
        confirmation_required = False
        confirmation_type = None
    elif decision_actionable:
        confirmation_required = True
        confirmation_type = "TRADE_CONFIRMATION"
    else:
        confirmation_required = True
        confirmation_type = "OVERRIDE_CONFIRMATION"

    return TradeAnalysisResult(
        symbol=symbol,
        market=market,
        action=action,
        momentum_score=momentum_score,
        momentum_total=4,
        momentum_level=momentum_level,
        portfolio_risk_status=portfolio_risk_status,
        decision_status=decision_status,
        hard_block=hard_block,
        override_allowed=override_allowed,
        confirmation_required=confirmation_required,
        confirmation_type=confirmation_type,
    )
