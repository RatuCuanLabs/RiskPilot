import unittest

from riskpilot.trading.exposure import calculate_post_trade_exposure
from riskpilot.trading.portfolio_snapshot import build_portfolio_snapshot
from riskpilot.risk.portfolio import Position


class TestPostTradeExposure(unittest.TestCase):

    def test_new_position_exposure(self):
        snapshot = build_portfolio_snapshot(
            total_trading_capital=1000.0,
            available_balance=1000.0,
            positions=[],
        )
        exposure = calculate_post_trade_exposure("BTC", snapshot, amount=100.0)
        self.assertAlmostEqual(exposure, 0.10)

    def test_adds_to_existing_position(self):
        snapshot = build_portfolio_snapshot(
            total_trading_capital=1000.0,
            available_balance=500.0,
            positions=[Position(symbol="BTC", value=200.0)],
        )
        exposure = calculate_post_trade_exposure("BTC", snapshot, amount=100.0)
        self.assertAlmostEqual(exposure, 0.30)

    def test_case_insensitive_symbol_match(self):
        snapshot = build_portfolio_snapshot(
            total_trading_capital=1000.0,
            available_balance=500.0,
            positions=[Position(symbol="btc", value=200.0)],
        )
        exposure = calculate_post_trade_exposure("BTC", snapshot, amount=100.0)
        self.assertAlmostEqual(exposure, 0.30)

    def test_zero_total_capital_returns_zero(self):
        snapshot = build_portfolio_snapshot(
            total_trading_capital=0.0,
            available_balance=0.0,
            positions=[],
        )
        exposure = calculate_post_trade_exposure("BTC", snapshot, amount=100.0)
        self.assertEqual(exposure, 0.0)

    def test_no_threshold_is_enforced_here(self):
        # This module only calculates; it must never raise or block,
        # even for a very large projected exposure.
        snapshot = build_portfolio_snapshot(
            total_trading_capital=100.0,
            available_balance=100.0,
            positions=[],
        )
        exposure = calculate_post_trade_exposure("BTC", snapshot, amount=100.0)
        self.assertAlmostEqual(exposure, 1.0)


if __name__ == "__main__":
    unittest.main()
