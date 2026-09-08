"""
RiskPilot Decision Engine
=========================

LOCKED DECISION MATRIX (exact strings, per the repeated "LOCKED" spec):
    PLATINUM (4/4) + LOW    -> "EXECUTE"
    GOLD     (3/4) + LOW    -> "BUY WITH NOTE"
    SILVER   (2/4) + LOW    -> "WAIT/HOLD"
    WAIT/HOLD (0-1/4) + LOW -> "WAIT/HOLD"
    ANY momentum   + HIGH   -> "WAIT/HOLD"   (High risk always overrides)
    ANY momentum   + MEDIUM -> "WAIT/HOLD"   (conservative default; the
                                              existing Phase 1-16 risk
                                              engine's MEDIUM tier has no
                                              defined trading-decision
                                              policy yet, so this is NOT
                                              silently treated as LOW or
                                              HIGH)

NOTE ON NAMING: a later spec draft used "BUY_WITH_NOTE" / "WAIT" instead
of "BUY WITH NOTE" / "WAIT/HOLD". That is a live open question — flagged
back to the requester rather than silently resolved. This implementation
keeps the original, repeatedly-confirmed LOCKED strings until that is
settled, to avoid shipping two contradictory literal values.

This module is pure and deterministic: no network calls, no Binance
AgentOS calls, no LLM. It classifies what the decision *should be* — it
does not execute anything itself.
"""

from dataclasses import dataclass
from typing import Optional, List

EXECUTE = "EXECUTE"
BUY_WITH_NOTE = "BUY WITH NOTE"
WAIT_HOLD = "WAIT/HOLD"

_VALID_DECISIONS = {EXECUTE, BUY_WITH_NOTE, WAIT_HOLD}
_VALID_MOMENTUM = {"PLATINUM", "GOLD", "SILVER", "WAIT/HOLD"}
_VALID_RISK = {"LOW", "MEDIUM", "HIGH"}


@dataclass(frozen=True)
class DecisionResult:
    momentum: str
    score: int
    risk: str
    decision: str
    actionable: bool
    reason: str
    indicator_summary: str
    risk_summary: str

    def as_dict(self) -> dict:
        return {
            "momentum": self.momentum,
            "score": self.score,
            "risk": self.risk,
            "decision": self.decision,
            "actionable": self.actionable,
            "reason": self.reason,
            "indicator_summary": self.indicator_summary,
            "risk_summary": self.risk_summary,
        }


class DecisionEngine:

    @classmethod
    def decide(
        cls,
        momentum: str,
        score: int,
        risk: str,
        fulfilled_indicators: Optional[List[str]] = None,
        unfulfilled_indicators: Optional[List[str]] = None,
        risk_reason: Optional[str] = None,
    ) -> DecisionResult:
        momentum_norm = (momentum or "").strip().upper()
        risk_norm = (risk or "").strip().upper()

        if momentum_norm not in _VALID_MOMENTUM:
            raise ValueError(f"Unknown momentum level: {momentum!r}. Expected one of {sorted(_VALID_MOMENTUM)}.")
        if risk_norm not in _VALID_RISK:
            raise ValueError(f"Unknown risk level: {risk!r}. Expected one of {sorted(_VALID_RISK)}.")
        if not isinstance(score, int) or not (0 <= score <= 4):
            raise ValueError(f"score must be an integer 0-4, got {score!r}")

        indicator_summary = cls._indicator_summary(score, fulfilled_indicators, unfulfilled_indicators)
        risk_summary = risk_reason or f"Portfolio/trading risk classified as {risk_norm}."

        if risk_norm == "HIGH":
            decision, actionable = WAIT_HOLD, False
            reason = (
                f"High risk detected. High risk always overrides momentum "
                f"({momentum_norm} {score}/4) -> {WAIT_HOLD}."
            )
        elif risk_norm == "MEDIUM":
            decision, actionable = WAIT_HOLD, False
            reason = (
                f"Medium risk has no locked decision policy yet, so this "
                f"engine does not silently treat it as LOW or HIGH. "
                f"Defaulting conservatively to {WAIT_HOLD} "
                f"(momentum was {momentum_norm} {score}/4)."
            )
        elif momentum_norm == "PLATINUM":
            decision, actionable = EXECUTE, True
            reason = f"Platinum momentum (4/4) with Low risk meets the highest confirmation threshold -> {EXECUTE}."
        elif momentum_norm == "GOLD":
            decision, actionable = BUY_WITH_NOTE, True
            reason = f"Gold momentum (3/4) with Low risk is a strong but not maximal setup -> {BUY_WITH_NOTE}."
        elif momentum_norm == "SILVER":
            decision, actionable = WAIT_HOLD, False
            reason = (
                f"Silver momentum (2/4) does not carry enough technical confirmation "
                f"to act, even with Low risk clearing the portfolio side -> {WAIT_HOLD}."
            )
        else:
            decision, actionable = WAIT_HOLD, False
            reason = f"{score}/4 indicators fulfilled is below the Silver threshold -> {WAIT_HOLD}."

        assert decision in _VALID_DECISIONS
        return DecisionResult(
            momentum=momentum_norm,
            score=score,
            risk=risk_norm,
            decision=decision,
            actionable=actionable,
            reason=reason,
            indicator_summary=indicator_summary,
            risk_summary=risk_summary,
        )

    @staticmethod
    def _indicator_summary(
        score: int,
        fulfilled_indicators: Optional[List[str]],
        unfulfilled_indicators: Optional[List[str]],
    ) -> str:
        if fulfilled_indicators is None and unfulfilled_indicators is None:
            return f"{score}/4 indicators fulfilled."
        fulfilled_str = ", ".join(fulfilled_indicators) if fulfilled_indicators else "none"
        unfulfilled_str = ", ".join(unfulfilled_indicators) if unfulfilled_indicators else "none"
        return f"{score}/4 fulfilled ({fulfilled_str}); not fulfilled: {unfulfilled_str}."
