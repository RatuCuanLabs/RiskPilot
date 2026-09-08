import itertools
import unittest

from riskpilot.momentum.engine import MomentumEngine, PLATINUM, GOLD, SILVER, WAIT_HOLD
from riskpilot.momentum.candles import Candle


def _make_candle(i, close, high=None, low=None, volume=100.0):
    return Candle(
        open=close,
        high=high if high is not None else close + 1,
        low=low if low is not None else close - 1,
        close=close,
        volume=volume,
        open_time_ms=i * 3_600_000,
        close_time_ms=(i + 1) * 3_600_000,
    )


class TestMomentumEngineScoring(unittest.TestCase):

    def test_all_four_true_is_platinum(self):
        result = MomentumEngine.score_conditions(rsi=True, macd=True, kdj=True, volume=True)
        self.assertEqual(result.score, 4)
        self.assertEqual(result.momentum, PLATINUM)

    def test_any_three_combination_is_gold(self):
        names = ["rsi", "macd", "kdj", "volume"]
        for combo in itertools.combinations(names, 3):
            kwargs = {name: (name in combo) for name in names}
            with self.subTest(combo=combo):
                result = MomentumEngine.score_conditions(**kwargs)
                self.assertEqual(result.score, 3)
                self.assertEqual(result.momentum, GOLD)

    def test_any_two_combination_is_silver(self):
        names = ["rsi", "macd", "kdj", "volume"]
        for combo in itertools.combinations(names, 2):
            kwargs = {name: (name in combo) for name in names}
            with self.subTest(combo=combo):
                result = MomentumEngine.score_conditions(**kwargs)
                self.assertEqual(result.score, 2)
                self.assertEqual(result.momentum, SILVER)

    def test_any_one_combination_is_wait_hold(self):
        names = ["rsi", "macd", "kdj", "volume"]
        for combo in itertools.combinations(names, 1):
            kwargs = {name: (name in combo) for name in names}
            with self.subTest(combo=combo):
                result = MomentumEngine.score_conditions(**kwargs)
                self.assertEqual(result.score, 1)
                self.assertEqual(result.momentum, WAIT_HOLD)

    def test_zero_true_is_wait_hold(self):
        result = MomentumEngine.score_conditions(rsi=False, macd=False, kdj=False, volume=False)
        self.assertEqual(result.score, 0)
        self.assertEqual(result.momentum, WAIT_HOLD)

    def test_no_special_pairing_required_for_silver(self):
        # RSI+KDJ (not the "usual" RSI+Volume) must still be SILVER.
        result = MomentumEngine.score_conditions(rsi=True, macd=False, kdj=True, volume=False)
        self.assertEqual(result.score, 2)
        self.assertEqual(result.momentum, SILVER)


class TestMomentumEngineCandleEvaluation(unittest.TestCase):

    def test_strong_uptrend_with_volume_spike_is_high_score(self):
        candles = [_make_candle(i, 100 + i * 0.8, volume=50.0) for i in range(60)]
        # Spike the final candle's volume well above the 20-period average.
        candles[-1] = _make_candle(59, candles[-1].close, volume=500.0)
        analysis = MomentumEngine.evaluate_candles(candles)
        self.assertTrue(analysis.rsi_fulfilled)
        self.assertTrue(analysis.macd_fulfilled)
        self.assertTrue(analysis.kdj_fulfilled)
        self.assertTrue(analysis.volume_fulfilled)
        self.assertEqual(analysis.score.momentum, PLATINUM)

    def test_strong_downtrend_is_wait_hold(self):
        candles = [_make_candle(i, 200 - i * 0.8, volume=50.0) for i in range(60)]
        analysis = MomentumEngine.evaluate_candles(candles)
        self.assertFalse(analysis.rsi_fulfilled)
        self.assertFalse(analysis.macd_fulfilled)
        self.assertFalse(analysis.kdj_fulfilled)
        self.assertEqual(analysis.score.momentum, WAIT_HOLD)

    def test_insufficient_candles_raises(self):
        candles = [_make_candle(i, 100 + i) for i in range(5)]
        with self.assertRaises(ValueError):
            MomentumEngine.evaluate_candles(candles)


if __name__ == "__main__":
    unittest.main()
