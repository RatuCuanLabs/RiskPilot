import unittest

from riskpilot.agentos.order_execution import DryRunOrderExecutor


class TestDryRunOrderExecutor(unittest.TestCase):

    def test_never_reports_live(self):
        executor = DryRunOrderExecutor()
        result = executor.place_market_order("BTCUSDT", "BUY", 50.0)
        self.assertFalse(result.is_live)

    def test_status_is_simulated_not_filled_or_submitted(self):
        executor = DryRunOrderExecutor()
        result = executor.place_market_order("BTCUSDT", "BUY", 50.0)
        self.assertEqual(result.status, "SIMULATED")
        self.assertNotIn(result.status, {"SUBMITTED", "FILLED"})

    def test_message_discloses_no_real_order_sent(self):
        executor = DryRunOrderExecutor()
        result = executor.place_market_order("BTCUSDT", "BUY", 50.0)
        self.assertIn("no real order", result.message.lower())

    def test_echoes_requested_parameters(self):
        executor = DryRunOrderExecutor()
        result = executor.place_market_order("ETHUSDT", "BUY", 75.0)
        self.assertEqual(result.symbol, "ETHUSDT")
        self.assertEqual(result.side, "BUY")
        self.assertEqual(result.requested_quote_amount, 75.0)


if __name__ == "__main__":
    unittest.main()
