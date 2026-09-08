"""
Market data interface for Binance AgentOS.

This is an abstraction only — a Protocol describing what a real
market-data provider must implement. There is no concrete
network-calling implementation here. This exists so the Momentum
Engine and trading flow can be developed and tested against a fake
implementation, and later pointed at a real one (e.g. one backed by
the connected Binance AgentOS klines tools) without changing any
calling code.
"""

from typing import List, Protocol

from riskpilot.momentum.candles import Candle


class CandleProvider(Protocol):
    def get_closed_candles(self, symbol: str, interval: str, limit: int) -> List[Candle]:
        """
        Must return only CLOSED candles, oldest first, most recent
        closed candle last. Implementations backed by a live exchange
        must filter out any still-forming candle themselves.
        """
        ...
