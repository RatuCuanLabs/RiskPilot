"""
Input snapshot for the Leverage & Liquidation Risk Engine.

This is a plain data holder. It does not fetch anything and does not
compute a risk classification itself. Critically: `current_risk_status`
and `post_trade_risk_status` are supplied BY THE CALLER (ultimately
backed by a real exchange/provider's own risk classification, once
wired via an AgentOS interface) rather than derived here from raw
margin numbers — deriving LOW/WARNING/CRITICAL from margin ratios would
require inventing a threshold or formula, which this engine must not do.
When a status is not supplied, the engine treats it as UNKNOWN rather
than guessing.

Fields left as None simply mean the provider did not supply that value.
"""

from dataclasses import dataclass
from typing import Optional

from .types import MarketType, RiskStatus


@dataclass(frozen=True)
class LeverageMarketSnapshot:
    market_type: MarketType
    leverage: Optional[float] = None
    margin_used: Optional[float] = None
    available_margin: Optional[float] = None
    maintenance_margin: Optional[float] = None
    liquidation_price: Optional[float] = None
    mark_price: Optional[float] = None

    # Already-classified statuses from the data provider. None means the
    # provider could not or did not supply a reliable classification.
    current_risk_status: Optional[RiskStatus] = None
    post_trade_risk_status: Optional[RiskStatus] = None
