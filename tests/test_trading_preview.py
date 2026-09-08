import unittest

from riskpilot.trading.preview import build_trade_preview


class TestTradePreview(unittest.TestCase):

    def test_preview_fields(self):
        preview = build_trade_preview(
            symbol="BTCUSDT",
            allocation_usdt=50.0,
            momentum="GOLD",
            momentum_score=3,
            risk="LOW",
            decision="BUY WITH NOTE",
        )
        d = preview.as_dict()
        self.assertEqual(d["symbol"], "BTCUSDT")
        self.assertEqual(d["allocation_usdt"], 50.0)
        self.assertEqual(d["decision"], "BUY WITH NOTE")

    def test_preview_render_contains_key_fields(self):
        preview = build_trade_preview(
            symbol="BTCUSDT",
            allocation_usdt=50.0,
            momentum="GOLD",
            momentum_score=3,
            risk="LOW",
            decision="BUY WITH NOTE",
        )
        rendered = preview.render()
        self.assertIn("BTCUSDT", rendered)
        self.assertIn("50.0", rendered)
        self.assertIn("GOLD", rendered)
        self.assertIn("BUY WITH NOTE", rendered)


if __name__ == "__main__":
    unittest.main()
