"""
Pure indicator math for the Momentum Engine.

Every function here is a stateless calculation over plain lists of
floats. No network access, no Binance client, no LLM involvement —
these are the deterministic building blocks the Momentum Engine composes.

Parameters match the LOCKED spec:
    RSI:    14
    MACD:   12, 26, 9
    KDJ:    N=9, K smoothing=3, D smoothing=3
    Volume: 20-period average
"""

from typing import List, Sequence, Tuple


def compute_rsi(closes: Sequence[float], period: int = 14) -> float:
    """Wilder's smoothed RSI over `closes`. Requires len(closes) >= period + 1."""
    if len(closes) < period + 1:
        raise ValueError(
            f"compute_rsi requires at least {period + 1} closes, got {len(closes)}"
        )
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0.0 for d in deltas]
    losses = [-d if d < 0 else 0.0 for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _ema_series(values: Sequence[float], period: int) -> List[float]:
    k = 2.0 / (period + 1)
    ema = [values[0]]
    for v in values[1:]:
        ema.append(v * k + ema[-1] * (1 - k))
    return ema


def compute_macd(
    closes: Sequence[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Tuple[float, float]:
    """
    Returns (macd_line, macd_signal) as of the last close.
    Requires len(closes) >= slow + signal for a stable result.
    """
    min_len = slow + signal
    if len(closes) < min_len:
        raise ValueError(
            f"compute_macd requires at least {min_len} closes, got {len(closes)}"
        )
    ema_fast = _ema_series(closes, fast)
    ema_slow = _ema_series(closes, slow)
    macd_line_series = [f - s for f, s in zip(ema_fast, ema_slow)]
    signal_series = _ema_series(macd_line_series, signal)
    return macd_line_series[-1], signal_series[-1]


def compute_kdj(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    n: int = 9,
    k_smoothing: int = 3,
    d_smoothing: int = 3,
) -> Tuple[float, float, float]:
    """
    Returns (K, D, J) as of the last close. K and D smoothing start from
    a neutral seed of 50, which is the conventional approach when no
    prior K/D history is available.
    Requires len(closes) >= n.
    """
    if len(closes) < n:
        raise ValueError(f"compute_kdj requires at least {n} closes, got {len(closes)}")

    rsv_list = []
    for i in range(n - 1, len(closes)):
        window_high = max(highs[i - n + 1 : i + 1])
        window_low = min(lows[i - n + 1 : i + 1])
        c = closes[i]
        rsv = 50.0 if window_high == window_low else (c - window_low) / (window_high - window_low) * 100.0
        rsv_list.append(rsv)

    k_values = [50.0]
    for rsv in rsv_list:
        k_values.append((k_values[-1] * (k_smoothing - 1) + rsv) / k_smoothing)
    k_values = k_values[1:]

    d_values = [50.0]
    for k in k_values:
        d_values.append((d_values[-1] * (d_smoothing - 1) + k) / d_smoothing)
    d_values = d_values[1:]

    j_value = 3 * k_values[-1] - 2 * d_values[-1]
    return k_values[-1], d_values[-1], j_value


def compute_volume_average(volumes: Sequence[float], period: int = 20) -> Tuple[float, float]:
    """
    Returns (current_volume, average_volume) where average_volume is the
    mean of the `period` candles immediately preceding the current one
    (the current candle is NOT included in its own average).
    Requires len(volumes) >= period + 1.
    """
    if len(volumes) < period + 1:
        raise ValueError(
            f"compute_volume_average requires at least {period + 1} volumes, got {len(volumes)}"
        )
    current_volume = volumes[-1]
    average_volume = sum(volumes[-(period + 1) : -1]) / period
    return current_volume, average_volume
