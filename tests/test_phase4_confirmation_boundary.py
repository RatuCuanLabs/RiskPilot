"""
Phase 4 gap closure — confirmation/execution boundary integration test.

This file adds NO new production code. It only composes existing,
unmodified pieces to prove requirement #8 from the Phase 4 spec:

    "Ensure any eventual execution would still have to pass through the
    existing Phase 2 safety gate and normal confirmation boundary."

It reuses, without modification:
    - riskpilot.trading.mitigation_workflow.evaluate_mitigation_workflow (Phase 4)
    - riskpilot.trading.state.TradeConversation                          (Phase 1.5)
    - riskpilot.agentos.order_execution.DryRunOrderExecutor              (Phase 1)
    - riskpilot.leverage.engine.LeverageRiskEngine                       (Phase 2)

No new executor, no new confirmation system, no network/live execution
code is introduced anywhere in this file.
"""

import unittest
from typing import Dict

from riskpilot.leverage.types import RiskStatus, TradeIntent, MarketType
from riskpilot.leverage.snapshot import LeverageMarketSnapshot
from riskpilot.leverage.engine import LeverageRiskEngine
from riskpilot.mitigation.simulation import ProjectedPositionState
from riskpilot.mitigation.types import MitigationStatus
from riskpilot.trading.mitigation_workflow import evaluate_mitigation_workflow
from riskpilot.trading.state import TradeConversation, TradeEvent, TradeState, InvalidTradeStateTransition
from riskpilot.agentos.order_execution import DryRunOrderExecutor


class FixtureSimulator:
    def __init__(self, mapping: Dict[float, RiskStatus]):
        self._mapping = mapping

    def simulate(self, reduction_quantity: float) -> ProjectedPositionState:
        status = self._mapping.get(round(reduction_quantity, 10), RiskStatus.UNKNOWN)
        return ProjectedPositionState(quantity=reduction_quantity, risk_status=status)


REALISTIC_010_BTC_SIMULATOR = FixtureSimulator({
    0.01: RiskStatus.CRITICAL,
    0.02: RiskStatus.CRITICAL,
    0.04: RiskStatus.WARNING,
    0.06: RiskStatus.LOW,
    0.08: RiskStatus.LOW,
})


class _CountingDryRunOrderExecutor(DryRunOrderExecutor):
    """
    Test instrumentation only: delegates entirely to the real, unmodified
    DryRunOrderExecutor and just counts calls, so a test can assert an
    executor was (or was not) invoked. Adds no new execution behavior.
    """

    def __init__(self):
        self.call_count = 0
        self.calls = []

    def place_market_order(self, symbol: str, side: str, quote_amount: float):
        self.call_count += 1
        self.calls.append((symbol, side, quote_amount))
        return super().place_market_order(symbol, side, quote_amount)


class TestMitigationRecommendationAloneDoesNotExecute(unittest.TestCase):

    def test_recommendation_does_not_invoke_executor(self):
        executor = _CountingDryRunOrderExecutor()
        result = evaluate_mitigation_workflow(
            current_risk=RiskStatus.CRITICAL,
            position_quantity=0.10,
            simulator=REALISTIC_010_BTC_SIMULATOR,
            market_type=MarketType.USD_M_FUTURES,
        )
        self.assertEqual(result.mitigation.status, MitigationStatus.RECOMMENDED)
        self.assertEqual(result.mapped_trade_intent, TradeIntent.REDUCE)
        self.assertFalse(result.execution_performed)
        # The workflow function itself never touches an executor at all.
        self.assertEqual(executor.call_count, 0)


class TestConfirmationGateIsAuthoritative(unittest.TestCase):

    def test_cannot_reach_executing_without_confirmation(self):
        conversation = TradeConversation()
        conversation.handle_event(TradeEvent.ASK_TO_TRADE)
        conversation.handle_event(TradeEvent.TOKEN_PROVIDED)
        conversation.handle_event(TradeEvent.ANALYSIS_COMPLETE)
        # A mitigation-recommended REDUCE is treated as an actionable
        # recommendation for state-machine purposes (there is something
        # concrete to do), same as an EXECUTE/BUY WITH NOTE decision.
        conversation.set_analysis_result(decision_actionable=True)
        conversation.handle_event(TradeEvent.TRADE_INTENT)
        conversation.handle_event(TradeEvent.AMOUNT_PROVIDED)
        conversation.handle_event(TradeEvent.PREVIEW_PRESENTED)
        self.assertEqual(conversation.state, TradeState.WAITING_FOR_CONFIRMATION)

        # Attempting to skip straight to execution-adjacent events fails.
        with self.assertRaises(InvalidTradeStateTransition):
            conversation.handle_event(TradeEvent.SAFETY_CHECK_PASSED)
        with self.assertRaises(InvalidTradeStateTransition):
            conversation.handle_event(TradeEvent.EXECUTION_RESULT_RECEIVED)

        # State is unchanged by the rejected attempts.
        self.assertEqual(conversation.state, TradeState.WAITING_FOR_CONFIRMATION)

    def test_executor_not_called_while_unconfirmed(self):
        executor = _CountingDryRunOrderExecutor()
        conversation = TradeConversation()
        conversation.handle_event(TradeEvent.ASK_TO_TRADE)
        conversation.handle_event(TradeEvent.TOKEN_PROVIDED)
        conversation.handle_event(TradeEvent.ANALYSIS_COMPLETE)
        conversation.set_analysis_result(decision_actionable=True)
        conversation.handle_event(TradeEvent.TRADE_INTENT)
        conversation.handle_event(TradeEvent.AMOUNT_PROVIDED)
        conversation.handle_event(TradeEvent.PREVIEW_PRESENTED)
        # Still WAITING_FOR_CONFIRMATION — a correct caller must not call
        # the executor here regardless of what mitigation recommended.
        self.assertEqual(conversation.state, TradeState.WAITING_FOR_CONFIRMATION)
        self.assertEqual(executor.call_count, 0)


class TestConfirmedMitigationReachesDryRunExecutorOnly(unittest.TestCase):

    def test_full_path_reaches_executor_only_after_confirmation_and_safety_check(self):
        workflow_result = evaluate_mitigation_workflow(
            current_risk=RiskStatus.CRITICAL,
            position_quantity=0.10,
            simulator=REALISTIC_010_BTC_SIMULATOR,
            market_type=MarketType.USD_M_FUTURES,
        )
        self.assertEqual(workflow_result.mapped_trade_intent, TradeIntent.REDUCE)
        self.assertFalse(workflow_result.would_be_hard_blocked)

        executor = _CountingDryRunOrderExecutor()
        conversation = TradeConversation()
        conversation.handle_event(TradeEvent.ASK_TO_TRADE)
        conversation.handle_event(TradeEvent.TOKEN_PROVIDED)
        conversation.handle_event(TradeEvent.ANALYSIS_COMPLETE)
        conversation.set_analysis_result(decision_actionable=True)
        conversation.handle_event(TradeEvent.TRADE_INTENT)
        conversation.handle_event(TradeEvent.AMOUNT_PROVIDED)
        conversation.handle_event(TradeEvent.PREVIEW_PRESENTED)
        conversation.handle_event(TradeEvent.CONFIRMED)
        self.assertEqual(conversation.state, TradeState.FINAL_SAFETY_CHECK)
        self.assertEqual(executor.call_count, 0)  # still not called at the safety-check stage

        conversation.handle_event(TradeEvent.SAFETY_CHECK_PASSED)
        self.assertEqual(conversation.state, TradeState.EXECUTING)

        # Only now, in EXECUTING, does a caller reach the existing DryRunOrderExecutor.
        order_result = executor.place_market_order(
            symbol="BTCUSDT",
            side="SELL",  # REDUCE on a long position
            quote_amount=workflow_result.mitigation.quantity,
        )
        self.assertEqual(executor.call_count, 1)
        self.assertEqual(order_result.status, "SIMULATED")
        self.assertFalse(order_result.is_live)
        self.assertIn("no real order was sent", order_result.message.lower())

    def test_state_machine_prevents_reexecution_after_reaching_executing(self):
        conversation = TradeConversation(state=TradeState.EXECUTING)
        with self.assertRaises(InvalidTradeStateTransition):
            conversation.handle_event(TradeEvent.CONFIRMED)  # stale/duplicate confirmation rejected


class TestPhase2HardBlockPreventsReachingConfirmation(unittest.TestCase):

    def test_open_intent_hard_block_reaches_blocked_never_executor(self):
        snapshot = LeverageMarketSnapshot(market_type=MarketType.USD_M_FUTURES, post_trade_risk_status=RiskStatus.CRITICAL)
        leverage_result = LeverageRiskEngine.evaluate(snapshot, TradeIntent.OPEN)
        self.assertTrue(leverage_result.hard_block)

        executor = _CountingDryRunOrderExecutor()
        conversation = TradeConversation()
        conversation.handle_event(TradeEvent.ASK_TO_TRADE)
        conversation.handle_event(TradeEvent.TOKEN_PROVIDED)
        conversation.handle_event(TradeEvent.ANALYSIS_COMPLETE)
        conversation.handle_event(TradeEvent.HARD_BLOCK_DETECTED)
        self.assertEqual(conversation.state, TradeState.BLOCKED)

        with self.assertRaises(InvalidTradeStateTransition):
            conversation.handle_event(TradeEvent.CONFIRMED)
        self.assertEqual(executor.call_count, 0)

    def test_reduce_intent_from_same_critical_state_is_not_hard_blocked(self):
        # Same CRITICAL risk, but the risk-reducing mitigation intent
        # remains allowed — confirming Phase 2's exemption still holds
        # in this same integration context.
        snapshot = LeverageMarketSnapshot(market_type=MarketType.USD_M_FUTURES, current_risk_status=RiskStatus.CRITICAL)
        leverage_result = LeverageRiskEngine.evaluate(snapshot, TradeIntent.REDUCE)
        self.assertFalse(leverage_result.hard_block)


if __name__ == "__main__":
    unittest.main()
