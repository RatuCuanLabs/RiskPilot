import unittest

from riskpilot.decision.engine import DecisionEngine, EXECUTE, BUY_WITH_NOTE, WAIT_HOLD


class TestDecisionEngine(unittest.TestCase):

    def test_platinum_low_risk_executes(self):
        result = DecisionEngine.decide(momentum="PLATINUM", score=4, risk="LOW")
        self.assertEqual(result.decision, EXECUTE)
        self.assertTrue(result.actionable)

    def test_gold_low_risk_buy_with_note(self):
        result = DecisionEngine.decide(momentum="GOLD", score=3, risk="LOW")
        self.assertEqual(result.decision, BUY_WITH_NOTE)
        self.assertTrue(result.actionable)

    def test_silver_low_risk_wait_hold(self):
        result = DecisionEngine.decide(momentum="SILVER", score=2, risk="LOW")
        self.assertEqual(result.decision, WAIT_HOLD)
        self.assertFalse(result.actionable)

    def test_one_of_four_low_risk_wait_hold(self):
        result = DecisionEngine.decide(momentum="WAIT/HOLD", score=1, risk="LOW")
        self.assertEqual(result.decision, WAIT_HOLD)

    def test_zero_of_four_low_risk_wait_hold(self):
        result = DecisionEngine.decide(momentum="WAIT/HOLD", score=0, risk="LOW")
        self.assertEqual(result.decision, WAIT_HOLD)

    def test_platinum_high_risk_wait_hold(self):
        result = DecisionEngine.decide(momentum="PLATINUM", score=4, risk="HIGH")
        self.assertEqual(result.decision, WAIT_HOLD)
        self.assertFalse(result.actionable)

    def test_gold_high_risk_wait_hold(self):
        result = DecisionEngine.decide(momentum="GOLD", score=3, risk="HIGH")
        self.assertEqual(result.decision, WAIT_HOLD)

    def test_silver_high_risk_wait_hold(self):
        result = DecisionEngine.decide(momentum="SILVER", score=2, risk="HIGH")
        self.assertEqual(result.decision, WAIT_HOLD)

    def test_high_risk_overrides_platinum_reason_mentions_override(self):
        result = DecisionEngine.decide(momentum="PLATINUM", score=4, risk="HIGH")
        self.assertIn("override", result.reason.lower())

    def test_medium_risk_is_conservative_wait_hold_for_all_momentum(self):
        for momentum, score in [("PLATINUM", 4), ("GOLD", 3), ("SILVER", 2), ("WAIT/HOLD", 1)]:
            with self.subTest(momentum=momentum):
                result = DecisionEngine.decide(momentum=momentum, score=score, risk="MEDIUM")
                self.assertEqual(result.decision, WAIT_HOLD)
                self.assertFalse(result.actionable)

    def test_medium_risk_not_silently_treated_as_low_or_high(self):
        result = DecisionEngine.decide(momentum="PLATINUM", score=4, risk="MEDIUM")
        self.assertIn("medium", result.reason.lower())
        self.assertNotIn("high risk detected", result.reason.lower())

    def test_decision_always_one_of_exactly_three_values(self):
        valid = {EXECUTE, BUY_WITH_NOTE, WAIT_HOLD}
        for momentum, score in [("PLATINUM", 4), ("GOLD", 3), ("SILVER", 2), ("WAIT/HOLD", 1), ("WAIT/HOLD", 0)]:
            for risk in ["LOW", "MEDIUM", "HIGH"]:
                with self.subTest(momentum=momentum, risk=risk):
                    result = DecisionEngine.decide(momentum=momentum, score=score, risk=risk)
                    self.assertIn(result.decision, valid)

    def test_indicator_summary_reflects_fulfilled_and_unfulfilled(self):
        result = DecisionEngine.decide(
            momentum="GOLD",
            score=3,
            risk="LOW",
            fulfilled_indicators=["RSI", "MACD", "Volume"],
            unfulfilled_indicators=["KDJ"],
        )
        self.assertIn("RSI", result.indicator_summary)
        self.assertIn("KDJ", result.indicator_summary)

    def test_invalid_momentum_raises(self):
        with self.assertRaises(ValueError):
            DecisionEngine.decide(momentum="BRONZE", score=2, risk="LOW")

    def test_invalid_risk_raises(self):
        with self.assertRaises(ValueError):
            DecisionEngine.decide(momentum="GOLD", score=3, risk="EXTREME")

    def test_invalid_score_raises(self):
        with self.assertRaises(ValueError):
            DecisionEngine.decide(momentum="GOLD", score=7, risk="LOW")

    def test_canonical_decision_literals_are_exact_strings(self):
        # Locks the exact literal values, not just the module constants,
        # so a future edit can't silently swap in "BUY_WITH_NOTE" / "WAIT" / "HOLD".
        self.assertEqual(EXECUTE, "EXECUTE")
        self.assertEqual(BUY_WITH_NOTE, "BUY WITH NOTE")
        self.assertEqual(WAIT_HOLD, "WAIT/HOLD")
        self.assertNotEqual(BUY_WITH_NOTE, "BUY_WITH_NOTE")
        self.assertNotEqual(WAIT_HOLD, "WAIT")
        self.assertNotEqual(WAIT_HOLD, "HOLD")


if __name__ == "__main__":
    unittest.main()
