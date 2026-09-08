"""
RiskPilot Momentum Engine
=========================

LOCKED SCORING RULE:
    4/4 fulfilled -> PLATINUM
    3/4 fulfilled -> GOLD
    2/4 fulfilled -> SILVER   (ANY 2-of-4 combination, no special pairing)
    0-1/4 fulfilled -> WAIT/HOLD

This module performs no network I/O and does not call an LLM. It is a
pure, deterministic scorer:
    - `MomentumEngine.score_conditions` scores four already-computed booleans.
    - `MomentumEngine.evaluate_candles` computes RSI/MACD/KDJ/Volume from a
      list of CLOSED candles and then scores them the same way.

The caller is responsible for ensuring `evaluate_candles` receives only
closed candles (see `momentum.candles.only_closed_candles`).
"""

from dataclasses import dataclass
from typing import List, Sequence

from .candles import Candle
from .indicators import compute_rsi, compute_macd, compute_kdj, compute_volume_average

PLATINUM = "PLATINUM"
GOLD = "GOLD"
SILVER = "SILVER"
WAIT_HOLD = "WAIT/HOLD"

_INDICATOR_NAMES = ("RSI", "MACD", "KDJ", "Volume")


@dataclass(frozen=True)
class MomentumScore:
    fulfilled_indicators: List[str]
    unfulfilled_indicators: List[str]
    score: int
    momentum: str
    reason: str

    def as_dict(self) -> dict:
        return {
            "fulfilled_indicators": self.fulfilled_indicators,
            "unfulfilled_indicators": self.unfulfilled_indicators,
            "score": self.score,
            "momentum": self.momentum,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class MomentumAnalysis:
    rsi: float
    macd_line: float
    macd_signal: float
    k: float
    d: float
    current_volume: float
    average_volume: float
    rsi_fulfilled: bool
    macd_fulfilled: bool
    kdj_fulfilled: bool
    volume_fulfilled: bool
    score: MomentumScore

    def as_dict(self) -> dict:
        return {
            "rsi": self.rsi,
            "macd_line": self.macd_line,
            "macd_signal": self.macd_signal,
            "k": self.k,
            "d": self.d,
            "current_volume": self.current_volume,
            "average_volume": self.average_volume,
            "rsi_fulfilled": self.rsi_fulfilled,
            "macd_fulfilled": self.macd_fulfilled,
            "kdj_fulfilled": self.kdj_fulfilled,
            "volume_fulfilled": self.volume_fulfilled,
            **self.score.as_dict(),
        }


def _score_to_momentum(score: int) -> str:
    if score == 4:
        return PLATINUM
    if score == 3:
        return GOLD
    if score == 2:
        return SILVER
    return WAIT_HOLD


class MomentumEngine:

    @staticmethod
    def score_conditions(rsi: bool, macd: bool, kdj: bool, volume: bool) -> MomentumScore:
        conditions = {"RSI": bool(rsi), "MACD": bool(macd), "KDJ": bool(kdj), "Volume": bool(volume)}
        fulfilled = [name for name in _INDICATOR_NAMES if conditions[name]]
        unfulfilled = [name for name in _INDICATOR_NAMES if not conditions[name]]
        score = len(fulfilled)
        momentum = _score_to_momentum(score)

        fulfilled_str = ", ".join(fulfilled) if fulfilled else "none"
        unfulfilled_str = ", ".join(unfulfilled) if unfulfilled else "none"
        reason = (
            f"{score}/4 indicators fulfilled ({fulfilled_str}); "
            f"not fulfilled: {unfulfilled_str}. "
            f"Any combination of {score} indicator(s) maps to {momentum} "
            f"under the locked scoring rule."
        )
        return MomentumScore(
            fulfilled_indicators=fulfilled,
            unfulfilled_indicators=unfulfilled,
            score=score,
            momentum=momentum,
            reason=reason,
        )

    @staticmethod
    def evaluate_candles(
        candles: Sequence[Candle],
        rsi_period: int = 14,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        kdj_n: int = 9,
        kdj_k_smoothing: int = 3,
        kdj_d_smoothing: int = 3,
        volume_period: int = 20,
    ) -> MomentumAnalysis:
        """
        Evaluate momentum from a list of CLOSED candles, oldest first,
        most recent closed candle last. Raises ValueError if there is not
        enough history to compute a stable result.
        """
        closes = [c.close for c in candles]
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        volumes = [c.volume for c in candles]

        rsi = compute_rsi(closes, period=rsi_period)
        macd_line, macd_signal_value = compute_macd(
            closes, fast=macd_fast, slow=macd_slow, signal=macd_signal
        )
        k, d, _j = compute_kdj(
            highs, lows, closes, n=kdj_n, k_smoothing=kdj_k_smoothing, d_smoothing=kdj_d_smoothing
        )
        current_volume, average_volume = compute_volume_average(volumes, period=volume_period)

        rsi_fulfilled = rsi > 50
        macd_fulfilled = macd_line > macd_signal_value
        kdj_fulfilled = k > d
        volume_fulfilled = current_volume > average_volume

        score = MomentumEngine.score_conditions(
            rsi=rsi_fulfilled, macd=macd_fulfilled, kdj=kdj_fulfilled, volume=volume_fulfilled
        )

        return MomentumAnalysis(
            rsi=rsi,
            macd_line=macd_line,
            macd_signal=macd_signal_value,
            k=k,
            d=d,
            current_volume=current_volume,
            average_volume=average_volume,
            rsi_fulfilled=rsi_fulfilled,
            macd_fulfilled=macd_fulfilled,
            kdj_fulfilled=kdj_fulfilled,
            volume_fulfilled=volume_fulfilled,
            score=score,
        )
