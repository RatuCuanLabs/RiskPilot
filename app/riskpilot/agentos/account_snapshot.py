"""
Account/portfolio snapshot interface for Binance AgentOS.

Abstraction only — describes what a real on-demand snapshot provider
must implement (called exactly twice per trade: once at analysis time,
once immediately before execution — never polled continuously). No
concrete network-calling implementation is provided in this phase.
"""

from typing import Protocol

from riskpilot.trading.portfolio_snapshot import PortfolioSnapshot


class AccountSnapshotProvider(Protocol):
    def get_snapshot(self) -> PortfolioSnapshot:
        ...
