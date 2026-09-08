"""
On-demand portfolio snapshot.

A plain data holder — this module does not fetch anything itself. It
exists so the trading flow can take exactly two snapshots (at analysis
time, and again immediately before execution) rather than continuously
polling. Fetching the real values is a separate concern, behind the
AgentOS AccountSnapshotProvider interface (see agentos/account_snapshot.py).
"""

from dataclasses import dataclass
from typing import List

from riskpilot.risk.portfolio import Position


@dataclass(frozen=True)
class PortfolioSnapshot:
    total_trading_capital: float
    available_balance: float
    positions: List[Position]


def build_portfolio_snapshot(
    total_trading_capital: float,
    available_balance: float,
    positions: List[Position],
) -> PortfolioSnapshot:
    return PortfolioSnapshot(
        total_trading_capital=total_trading_capital,
        available_balance=available_balance,
        positions=positions,
    )
