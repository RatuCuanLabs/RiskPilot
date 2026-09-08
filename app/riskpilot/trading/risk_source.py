"""
Trading risk source.

This does NOT implement a new risk engine. It is a thin adapter that
feeds the existing Phase 1-16 concentration-risk audit and WHY explainer
into the Decision Engine as the "risk" input for a trade decision, per
the instruction that "existing RiskPilot concentration risk is the
source of the risk assessment."

If a different, trade-specific risk source (e.g. post-trade exposure)
is wanted later, it belongs in a new function here — the existing
audit_portfolio/explain_concentration_risk functions in risk/ and why/
are reused unmodified.
"""

from dataclasses import dataclass
from typing import List

from riskpilot.audit.auditor import audit_portfolio, PortfolioAudit
from riskpilot.risk.portfolio import Position
from riskpilot.why.explainer import explain_concentration_risk


@dataclass(frozen=True)
class TradingRiskAssessment:
    risk: str
    reason: str
    audit: PortfolioAudit


def assess_trading_risk(positions: List[Position]) -> TradingRiskAssessment:
    audit = audit_portfolio(positions)
    reason = explain_concentration_risk(audit)
    return TradingRiskAssessment(risk=audit.concentration_risk, reason=reason, audit=audit)
