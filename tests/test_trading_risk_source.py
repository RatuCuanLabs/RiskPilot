import unittest

from riskpilot.trading.risk_source import assess_trading_risk
from riskpilot.risk.portfolio import Position


class TestTradingRiskSource(unittest.TestCase):

    def test_low_concentration_is_low_risk(self):
        positions = [
            Position(symbol="BTC", value=100.0),
            Position(symbol="ETH", value=100.0),
            Position(symbol="SOL", value=100.0),
            Position(symbol="BNB", value=100.0),
        ]
        assessment = assess_trading_risk(positions)
        self.assertEqual(assessment.risk, "LOW")
        self.assertIsInstance(assessment.reason, str)
        self.assertTrue(len(assessment.reason) > 0)

    def test_high_concentration_is_high_risk(self):
        positions = [
            Position(symbol="BTC", value=900.0),
            Position(symbol="ETH", value=100.0),
        ]
        assessment = assess_trading_risk(positions)
        self.assertEqual(assessment.risk, "HIGH")

    def test_medium_concentration_is_medium_risk(self):
        positions = [
            Position(symbol="BTC", value=400.0),
            Position(symbol="ETH", value=300.0),
            Position(symbol="SOL", value=300.0),
        ]
        assessment = assess_trading_risk(positions)
        self.assertEqual(assessment.risk, "MEDIUM")

    def test_empty_portfolio_is_low_risk(self):
        assessment = assess_trading_risk([])
        self.assertEqual(assessment.risk, "LOW")


if __name__ == "__main__":
    unittest.main()
