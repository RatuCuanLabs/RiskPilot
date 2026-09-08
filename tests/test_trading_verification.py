import unittest

from riskpilot.trading.verification import verify_trade_execution


class TestTradingVerification(unittest.TestCase):

    def test_matching_amounts_verified(self):
        result = verify_trade_execution("BTCUSDT", expected_quote_amount=50.0, actual_quote_amount=50.0)
        self.assertEqual(result.status, "VERIFIED")

    def test_mismatched_amounts_fail(self):
        result = verify_trade_execution("BTCUSDT", expected_quote_amount=50.0, actual_quote_amount=10.0)
        self.assertEqual(result.status, "FAILED")

    def test_within_tolerance_verified(self):
        result = verify_trade_execution(
            "BTCUSDT", expected_quote_amount=50.0, actual_quote_amount=50.005, tolerance=0.01
        )
        self.assertEqual(result.status, "VERIFIED")


if __name__ == "__main__":
    unittest.main()
