"""
Candle data structures for the Momentum Engine.

Pure data holders + conversion helpers. No network calls, no Binance
client code lives here — this module only knows how to turn already
retrieved kline rows into a typed, closed-candle list.
"""

from dataclasses import dataclass
from typing import List, Sequence, Union


@dataclass(frozen=True)
class Candle:
    open: float
    high: float
    low: float
    close: float
    volume: float
    open_time_ms: int
    close_time_ms: int


def candle_from_binance_kline(kline: Sequence[Union[str, int]]) -> Candle:
    """
    Convert a single Binance-style kline row (as returned by e.g.
    spot.klines / spot.uiKlines) into a Candle.

    Expected row shape (index -> field), matching Binance's public API:
        0  open time
        1  open
        2  high
        3  low
        4  close
        5  volume
        6  close time
        ... (remaining fields ignored)
    """
    return Candle(
        open=float(kline[1]),
        high=float(kline[2]),
        low=float(kline[3]),
        close=float(kline[4]),
        volume=float(kline[5]),
        open_time_ms=int(kline[0]),
        close_time_ms=int(kline[6]),
    )


def candles_from_binance_klines(klines: Sequence[Sequence[Union[str, int]]]) -> List[Candle]:
    return [candle_from_binance_kline(k) for k in klines]


def only_closed_candles(candles: Sequence[Candle], now_ms: int) -> List[Candle]:
    """
    Drop any candle whose close time has not yet passed — i.e. the
    currently-forming candle. The Momentum Engine must only ever be
    evaluated against closed candles.
    """
    return [c for c in candles if c.close_time_ms < now_ms]
