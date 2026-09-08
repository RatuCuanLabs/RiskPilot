"""
RiskPilot Leverage & Liquidation Risk Engine.

Core principle (unchanged from spec):
    Claude does not calculate leverage risk. Claude does not determine
    liquidation safety. RiskPilot determines leveraged risk and returns
    a structured result.

This engine does NOT invent liquidation formulas, maintenance-margin
formulas, leverage thresholds, Binance risk tiers, or margin-call
percentages. It classifies risk using whatever status the data
provider already supplied (`current_risk_status` / `post_trade_risk_status`
on the input snapshot); when that is missing, the result is UNKNOWN —
never guessed as safe.

The only arithmetic performed here is `mark_price - liquidation_price`
for `liquidation_distance`, which is plain subtraction of two
already-known values, not a risk formula or threshold.

HARD BLOCK RULE (non-overridable):
    Risk-increasing intents (OPEN, ADD, HEDGE) + evaluated risk of
    CRITICAL or UNKNOWN -> hard_block = True, override_allowed = False.
    Risk-reducing intents (REDUCE, CLOSE) are never hard-blocked by this
    engine, regardless of current or post-trade risk — reducing risk
    must not be prevented by the same gate that prevents increasing it.

Momentum independence: this module has no knowledge of the Momentum or
Decision engines at all. The `leverage.combine` module is what wires
the "momentum can never override a leverage hard block" rule, and it
does so by always checking `hard_block` first — never by asking this
engine to consider momentum.
"""

from dataclasses import dataclass
from typing import Optional

from .types import MarketType, RiskStatus, TradeIntent, RISK_INCREASING_INTENTS, RISK_REDUCING_INTENTS
from .snapshot import LeverageMarketSnapshot


@dataclass(frozen=True)
class LeverageRiskResult:
    market_type: MarketType
    intent: TradeIntent
    risk_status: RiskStatus  # the status actually used for the hard-block decision
    current_risk_status: RiskStatus
    post_trade_risk: RiskStatus
    leverage: Optional[float]
    margin_used: Optional[float]
    available_margin: Optional[float]
    maintenance_margin: Optional[float]
    liquidation_price: Optional[float]
    mark_price: Optional[float]
    liquidation_distance: Optional[float]
    hard_block: bool
    override_allowed: bool
    mitigation_required: bool

    def as_dict(self) -> dict:
        return {
            "market_type": self.market_type.value,
            "intent": self.intent.value,
            "risk_status": self.risk_status.value,
            "current_risk_status": self.current_risk_status.value,
            "post_trade_risk": self.post_trade_risk.value,
            "leverage": self.leverage,
            "margin_used": self.margin_used,
            "available_margin": self.available_margin,
            "maintenance_margin": self.maintenance_margin,
            "liquidation_price": self.liquidation_price,
            "mark_price": self.mark_price,
            "liquidation_distance": self.liquidation_distance,
            "hard_block": self.hard_block,
            "override_allowed": self.override_allowed,
            "mitigation": {"required": self.mitigation_required},
        }


class LeverageRiskEngine:

    @staticmethod
    def evaluate(snapshot: LeverageMarketSnapshot, intent: TradeIntent) -> LeverageRiskResult:
        if snapshot.market_type == MarketType.SPOT:
            return LeverageRiskResult(
                market_type=MarketType.SPOT,
                intent=intent,
                risk_status=RiskStatus.NOT_APPLICABLE,
                current_risk_status=RiskStatus.NOT_APPLICABLE,
                post_trade_risk=RiskStatus.NOT_APPLICABLE,
                leverage=None,
                margin_used=None,
                available_margin=None,
                maintenance_margin=None,
                liquidation_price=None,
                mark_price=None,
                liquidation_distance=None,
                hard_block=False,
                override_allowed=True,
                mitigation_required=False,
            )

        # Leveraged market (MARGIN_SPOT / USD_M_FUTURES / COIN_M_FUTURES).
        current_status = snapshot.current_risk_status or RiskStatus.UNKNOWN

        risk_increasing = intent in RISK_INCREASING_INTENTS
        risk_reducing = intent in RISK_REDUCING_INTENTS

        if risk_increasing:
            # Post-trade evaluation is mandatory for OPEN/ADD/HEDGE. Missing
            # post-trade classification is treated as UNKNOWN, never as safe.
            post_trade_status = snapshot.post_trade_risk_status or RiskStatus.UNKNOWN
            evaluated_status = post_trade_status
        else:
            # REDUCE/CLOSE: post-trade evaluation isn't mandatory for the
            # block decision (risk-reducing actions are exempt from the
            # hard-block gate below), but we still report honestly what we
            # know, without inventing a value if the provider gave none.
            post_trade_status = snapshot.post_trade_risk_status or RiskStatus.UNKNOWN
            evaluated_status = current_status

        if risk_reducing:
            hard_block = False
        else:
            hard_block = evaluated_status in (RiskStatus.CRITICAL, RiskStatus.UNKNOWN)

        override_allowed = not hard_block

        liquidation_distance = None
        if snapshot.mark_price is not None and snapshot.liquidation_price is not None:
            liquidation_distance = snapshot.mark_price - snapshot.liquidation_price

        mitigation_required = evaluated_status in (RiskStatus.WARNING, RiskStatus.CRITICAL)

        return LeverageRiskResult(
            market_type=snapshot.market_type,
            intent=intent,
            risk_status=evaluated_status,
            current_risk_status=current_status,
            post_trade_risk=post_trade_status,
            leverage=snapshot.leverage,
            margin_used=snapshot.margin_used,
            available_margin=snapshot.available_margin,
            maintenance_margin=snapshot.maintenance_margin,
            liquidation_price=snapshot.liquidation_price,
            mark_price=snapshot.mark_price,
            liquidation_distance=liquidation_distance,
            hard_block=hard_block,
            override_allowed=override_allowed,
            mitigation_required=mitigation_required,
        )
