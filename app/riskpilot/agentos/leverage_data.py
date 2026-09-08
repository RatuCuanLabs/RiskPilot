"""
Leverage/margin/liquidation data interface for Binance AgentOS.

Abstraction only — a Protocol describing what a real provider must
implement (account snapshot, position snapshot, margin info, mark
price, liquidation price, leverage, maintenance margin, available
margin). There is no concrete network-calling implementation here.
RiskPilot's LeverageRiskEngine only ever consumes the already-typed
LeverageMarketSnapshot this provider would produce — it never talks to
AgentOS or Binance directly.
"""

from typing import Protocol

from riskpilot.leverage.snapshot import LeverageMarketSnapshot
from riskpilot.leverage.types import TradeIntent


class LeverageDataProvider(Protocol):
    def get_leverage_snapshot(self, symbol: str, intent: TradeIntent) -> LeverageMarketSnapshot:
        """
        Must return a LeverageMarketSnapshot for the given symbol and
        proposed trade intent. Any field the underlying exchange/account
        data cannot reliably supply must be left as None on the
        snapshot — never estimated or assumed safe.
        """
        ...
