import unittest

from riskpilot.trading.hard_safety import HardSafetyEngine, MIN_TRADE_USDT
from riskpilot.trading.portfolio_snapshot import build_portfolio_snapshot
from riskpilot.risk.portfolio import Position


def _snapshot(total_capital=1000.0, available=500.0, positions=None):
    return build_portfolio_snapshot(
        total_trading_capital=total_capital,
        available_balance=available,
        positions=positions or [],
    )


class TestHardSafetyEngine(unittest.TestCase):

    def test_valid_trade_no_block(self):
        snapshot = _snapshot(total_capital=1000.0, available=500.0)
        result = HardSafetyEngine.check(symbol_supported=True, amount=100.0, snapshot=snapshot)
        self.assertFalse(result.hard_block)
        self.assertTrue(result.override_allowed)
        self.assertEqual(result.violations, [])

    def test_unsupported_symbol_blocks(self):
        snapshot = _snapshot()
        result = HardSafetyEngine.check(symbol_supported=False, amount=100.0, snapshot=snapshot)
        self.assertTrue(result.hard_block)
        self.assertFalse(result.override_allowed)

    def test_insufficient_balance_blocks(self):
        snapshot = _snapshot(total_capital=1000.0, available=50.0)
        result = HardSafetyEngine.check(symbol_supported=True, amount=100.0, snapshot=snapshot)
        self.assertTrue(result.hard_block)
        self.assertTrue(any("balance" in v.lower() for v in result.violations))

    def test_below_minimum_order_blocks(self):
        snapshot = _snapshot(total_capital=1000.0, available=500.0)
        result = HardSafetyEngine.check(symbol_supported=True, amount=MIN_TRADE_USDT - 1, snapshot=snapshot)
        self.assertTrue(result.hard_block)
        self.assertTrue(any("minimum" in v.lower() for v in result.violations))

    def test_invalid_amount_blocks(self):
        snapshot = _snapshot()
        result = HardSafetyEngine.check(symbol_supported=True, amount=0, snapshot=snapshot)
        self.assertTrue(result.hard_block)

    def test_exactly_20_percent_of_total_capital_allowed(self):
        # Total capital = $100, new trade = $20 -> exactly 20%, must be allowed.
        snapshot = _snapshot(total_capital=100.0, available=20.0)
        result = HardSafetyEngine.check(symbol_supported=True, amount=20.0, snapshot=snapshot)
        self.assertFalse(result.hard_block)

    def test_below_20_percent_allowed(self):
        snapshot = _snapshot(total_capital=100.0, available=15.0)
        result = HardSafetyEngine.check(symbol_supported=True, amount=15.0, snapshot=snapshot)
        self.assertFalse(result.hard_block)

    def test_above_20_percent_blocked(self):
        snapshot = _snapshot(total_capital=100.0, available=25.0)
        result = HardSafetyEngine.check(symbol_supported=True, amount=25.0, snapshot=snapshot)
        self.assertTrue(result.hard_block)
        self.assertTrue(any("allocation" in v.lower() for v in result.violations))

    def test_20_percent_is_of_total_capital_not_remaining_balance(self):
        # Total capital = $100, already deployed = $80, available = $20,
        # new trade = $20 -> 20% of TOTAL capital -> allowed, even though
        # it is 100% of the *remaining* balance.
        snapshot = _snapshot(total_capital=100.0, available=20.0)
        result = HardSafetyEngine.check(symbol_supported=True, amount=20.0, snapshot=snapshot)
        self.assertFalse(result.hard_block)

    def test_zero_total_capital_blocks(self):
        snapshot = _snapshot(total_capital=0.0, available=500.0)
        result = HardSafetyEngine.check(symbol_supported=True, amount=100.0, snapshot=snapshot)
        self.assertTrue(result.hard_block)


if __name__ == "__main__":
    unittest.main()
