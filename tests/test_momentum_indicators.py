import unittest

from riskpilot.momentum.indicators import (
    compute_rsi,
    compute_macd,
    compute_kdj,
    compute_volume_average,
)


class TestIndicators(unittest.TestCase):

    def test_rsi_all_gains_is_100(self):
        closes = [float(i) for i in range(1, 20)]  # strictly increasing
        rsi = compute_rsi(closes, period=14)
        self.assertEqual(rsi, 100.0)

    def test_rsi_all_losses_is_0(self):
        closes = [float(i) for i in range(20, 1, -1)]  # strictly decreasing
        rsi = compute_rsi(closes, period=14)
        self.assertEqual(rsi, 0.0)

    def test_rsi_insufficient_data_raises(self):
        with self.assertRaises(ValueError):
            compute_rsi([1.0, 2.0, 3.0], period=14)

    def test_macd_uptrend_line_above_signal(self):
        closes = [100 + i * 0.5 for i in range(60)]  # steady uptrend
        macd_line, signal = compute_macd(closes, fast=12, slow=26, signal=9)
        self.assertGreater(macd_line, signal)

    def test_macd_downtrend_line_below_signal(self):
        closes = [200 - i * 0.5 for i in range(60)]  # steady downtrend
        macd_line, signal = compute_macd(closes, fast=12, slow=26, signal=9)
        self.assertLess(macd_line, signal)

    def test_macd_insufficient_data_raises(self):
        with self.assertRaises(ValueError):
            compute_macd([1.0] * 10, fast=12, slow=26, signal=9)

    def test_kdj_uptrend_k_above_d(self):
        n = 15
        closes = [100 + i for i in range(n)]
        highs = [c + 1 for c in closes]
        lows = [c - 1 for c in closes]
        k, d, j = compute_kdj(highs, lows, closes, n=9, k_smoothing=3, d_smoothing=3)
        self.assertGreater(k, d)

    def test_kdj_downtrend_k_below_d(self):
        n = 15
        closes = [200 - i for i in range(n)]
        highs = [c + 1 for c in closes]
        lows = [c - 1 for c in closes]
        k, d, j = compute_kdj(highs, lows, closes, n=9, k_smoothing=3, d_smoothing=3)
        self.assertLess(k, d)

    def test_kdj_insufficient_data_raises(self):
        with self.assertRaises(ValueError):
            compute_kdj([1.0] * 3, [1.0] * 3, [1.0] * 3, n=9)

    def test_volume_average_excludes_current_candle(self):
        volumes = [10.0] * 20 + [999.0]  # 20 candles avg 10, latest is 999
        current, average = compute_volume_average(volumes, period=20)
        self.assertEqual(current, 999.0)
        self.assertEqual(average, 10.0)

    def test_volume_average_insufficient_data_raises(self):
        with self.assertRaises(ValueError):
            compute_volume_average([1.0] * 5, period=20)


if __name__ == "__main__":
    unittest.main()
