import unittest

from riskpilot.decision.engine import DecisionEngine, EXECUTE, BUY_WITH_NOTE, WAIT_HOLD
from riskpilot.leverage.types import MarketType, RiskStatus, TradeIntent
from riskpilot.leverage.snapshot import LeverageMarketSnapshot
from riskpilot.leverage.engine import LeverageRiskEngine
from riskpilot.leverage.combine import combine_decision_with_leverage_risk, HARD_BLOCK


def _critical_open_leverage_result():
    snapshot = LeverageMarketSnapshot(
        market_type=MarketType.USD_M_FUTURES,
        current_risk_status=RiskStatus.WARNING,
        post_trade_risk_status=RiskStatus.CRITICAL,
    )
    return LeverageRiskEngine.evaluate(snapshot, TradeIntent.OPEN)


class TestMomentumCannotOverrideLeverageHardBlock(unittest.TestCase):

    def test_platinum_execute_still_hard_blocked_by_critical_leverage(self):
        decision = DecisionEngine.decide(momentum="PLATINUM", score=4, risk="LOW")
        self.assertEqual(decision.decision, EXECUTE)  # momentum alone says EXECUTE
        verdict = combine_decision_with_leverage_risk(decision, _critical_open_leverage_result())
        self.assertEqual(verdict.final_action, HARD_BLOCK)
        self.assertNotEqual(verdict.final_action, EXECUTE)
        self.assertTrue(verdict.hard_block)
        self.assertFalse(verdict.override_allowed)

    def test_gold_buy_with_note_still_hard_blocked_by_critical_leverage(self):
        decision = DecisionEngine.decide(momentum="GOLD", score=3, risk="LOW")
        self.assertEqual(decision.decision, BUY_WITH_NOTE)
        verdict = combine_decision_with_leverage_risk(decision, _critical_open_leverage_result())
        self.assertEqual(verdict.final_action, HARD_BLOCK)

    def test_silver_wait_hold_still_hard_blocked_by_critical_leverage(self):
        decision = DecisionEngine.decide(momentum="SILVER", score=2, risk="LOW")
        self.assertEqual(decision.decision, WAIT_HOLD)
        verdict = combine_decision_with_leverage_risk(decision, _critical_open_leverage_result())
        self.assertEqual(verdict.final_action, HARD_BLOCK)

    def test_wait_hold_momentum_still_hard_blocked_by_critical_leverage(self):
        decision = DecisionEngine.decide(momentum="WAIT/HOLD", score=1, risk="LOW")
        self.assertEqual(decision.decision, WAIT_HOLD)
        verdict = combine_decision_with_leverage_risk(decision, _critical_open_leverage_result())
        self.assertEqual(verdict.final_action, HARD_BLOCK)

    def test_unknown_leverage_also_overrides_platinum_execute(self):
        decision = DecisionEngine.decide(momentum="PLATINUM", score=4, risk="LOW")
        snapshot = LeverageMarketSnapshot(market_type=MarketType.USD_M_FUTURES, post_trade_risk_status=None)
        leverage_result = LeverageRiskEngine.evaluate(snapshot, TradeIntent.OPEN)
        self.assertTrue(leverage_result.hard_block)
        verdict = combine_decision_with_leverage_risk(decision, leverage_result)
        self.assertEqual(verdict.final_action, HARD_BLOCK)

    def test_no_leverage_hard_block_lets_momentum_decision_stand(self):
        decision = DecisionEngine.decide(momentum="PLATINUM", score=4, risk="LOW")
        snapshot = LeverageMarketSnapshot(
            market_type=MarketType.USD_M_FUTURES,
            current_risk_status=RiskStatus.LOW,
            post_trade_risk_status=RiskStatus.LOW,
        )
        leverage_result = LeverageRiskEngine.evaluate(snapshot, TradeIntent.OPEN)
        self.assertFalse(leverage_result.hard_block)
        verdict = combine_decision_with_leverage_risk(decision, leverage_result)
        self.assertEqual(verdict.final_action, EXECUTE)

    def test_spot_not_applicable_never_blocks_momentum_decision(self):
        decision = DecisionEngine.decide(momentum="GOLD", score=3, risk="LOW")
        snapshot = LeverageMarketSnapshot(market_type=MarketType.SPOT)
        leverage_result = LeverageRiskEngine.evaluate(snapshot, TradeIntent.OPEN)
        verdict = combine_decision_with_leverage_risk(decision, leverage_result)
        self.assertEqual(verdict.final_action, BUY_WITH_NOTE)


if __name__ == "__main__":
    unittest.main()
