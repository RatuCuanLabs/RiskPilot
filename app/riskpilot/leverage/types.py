"""
Enums for the Leverage & Liquidation Risk Engine.

Exactly the literals specified — no additional risk-status or market-type
values are invented.
"""

from enum import Enum


class MarketType(str, Enum):
    SPOT = "SPOT"
    MARGIN_SPOT = "MARGIN_SPOT"
    USD_M_FUTURES = "USD_M_FUTURES"
    COIN_M_FUTURES = "COIN_M_FUTURES"


class RiskStatus(str, Enum):
    LOW = "LOW"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class TradeIntent(str, Enum):
    OPEN = "OPEN"
    ADD = "ADD"
    REDUCE = "REDUCE"
    CLOSE = "CLOSE"
    HEDGE = "HEDGE"


LEVERAGED_MARKET_TYPES = (MarketType.MARGIN_SPOT, MarketType.USD_M_FUTURES, MarketType.COIN_M_FUTURES)
RISK_INCREASING_INTENTS = (TradeIntent.OPEN, TradeIntent.ADD, TradeIntent.HEDGE)
RISK_REDUCING_INTENTS = (TradeIntent.REDUCE, TradeIntent.CLOSE)
