import unittest

from riskpilot.trading.result import build_trade_analysis_result


class TestTradeAnalysisResult(unittest.TestCase):

    def test_actionable_decision_requires_trade_confirmation(self):
        result = build_trade_analysis_result(
            symbol="BTCUSDT",
            momentum_score=4,
            momentum_level="PLATINUM",
            portfolio_risk_status="LOW",
            decision_status="EXECUTE",
            decision_actionable=True,
            hard_block=False,
        )
        d = result.as_dict()
        self.assertTrue(d["confirmation"]["required"])
        self.assertEqual(d["confirmation"]["type"], "TRADE_CONFIRMATION")
        self.assertFalse(d["decision"]["hard_block"])
        self.assertTrue(d["decision"]["override_allowed"])
        self.assertEqual(d["decision"]["status"], "EXECUTE")

    def test_wait_hold_requires_override_confirmation(self):
        result = build_trade_analysis_result(
            symbol="BTCUSDT",
            momentum_score=2,
            momentum_level="SILVER",
            portfolio_risk_status="LOW",
            decision_status="WAIT/HOLD",
            decision_actionable=False,
            hard_block=False,
        )
        d = result.as_dict()
        self.assertTrue(d["confirmation"]["required"])
        self.assertEqual(d["confirmation"]["type"], "OVERRIDE_CONFIRMATION")
        self.assertTrue(d["decision"]["override_allowed"])

    def test_hard_block_requires_no_confirmation(self):
        result = build_trade_analysis_result(
            symbol="BTCUSDT",
            momentum_score=2,
            momentum_level="SILVER",
            portfolio_risk_status="LOW",
            decision_status="WAIT/HOLD",
            decision_actionable=False,
            hard_block=True,
        )
        d = result.as_dict()
        self.assertFalse(d["confirmation"]["required"])
        self.assertIsNone(d["confirmation"]["type"])
        self.assertTrue(d["decision"]["hard_block"])
        self.assertFalse(d["decision"]["override_allowed"])

    def test_schema_shape_matches_spec(self):
        result = build_trade_analysis_result(
            symbol="BTCUSDT",
            momentum_score=2,
            momentum_level="SILVER",
            portfolio_risk_status="LOW",
            decision_status="WAIT/HOLD",
            decision_actionable=False,
            hard_block=False,
        )
        d = result.as_dict()
        self.assertEqual(
            set(d.keys()),
            {"request_id", "symbol", "market", "action", "momentum", "portfolio_risk", "decision", "confirmation"},
        )
        self.assertEqual(set(d["momentum"].keys()), {"score", "total", "level"})
        self.assertEqual(d["momentum"]["total"], 4)

    def test_request_id_is_generated_and_unique(self):
        r1 = build_trade_analysis_result(
            symbol="BTCUSDT", momentum_score=4, momentum_level="PLATINUM",
            portfolio_risk_status="LOW", decision_status="EXECUTE",
            decision_actionable=True, hard_block=False,
        )
        r2 = build_trade_analysis_result(
            symbol="BTCUSDT", momentum_score=4, momentum_level="PLATINUM",
            portfolio_risk_status="LOW", decision_status="EXECUTE",
            decision_actionable=True, hard_block=False,
        )
        self.assertNotEqual(r1.request_id, r2.request_id)


if __name__ == "__main__":
    unittest.main()
