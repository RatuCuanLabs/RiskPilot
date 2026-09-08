import unittest

from riskpilot.trading.state import TradeConversation, TradeState, TradeEvent, InvalidTradeStateTransition


class TestTradeStateMachineActionablePath(unittest.TestCase):
    """EXECUTE / BUY WITH NOTE: no override gate needed."""

    def test_happy_path_actionable_decision(self):
        c = TradeConversation()
        c.handle_event(TradeEvent.ASK_TO_TRADE)
        c.handle_event(TradeEvent.TOKEN_PROVIDED)
        c.handle_event(TradeEvent.ANALYSIS_COMPLETE)
        c.set_analysis_result(decision_actionable=True)
        self.assertEqual(c.handle_event(TradeEvent.TRADE_INTENT), TradeState.WAITING_FOR_AMOUNT)
        self.assertEqual(c.handle_event(TradeEvent.AMOUNT_PROVIDED), TradeState.PREVIEW_READY)
        self.assertEqual(c.handle_event(TradeEvent.PREVIEW_PRESENTED), TradeState.WAITING_FOR_CONFIRMATION)
        self.assertEqual(c.handle_event(TradeEvent.CONFIRMED), TradeState.FINAL_SAFETY_CHECK)
        self.assertEqual(c.handle_event(TradeEvent.SAFETY_CHECK_PASSED), TradeState.EXECUTING)
        self.assertEqual(c.handle_event(TradeEvent.EXECUTION_RESULT_RECEIVED), TradeState.VERIFYING)
        self.assertEqual(c.handle_event(TradeEvent.VERIFICATION_COMPLETE), TradeState.COMPLETE)

    def test_cannot_skip_final_safety_check(self):
        c = TradeConversation(state=TradeState.WAITING_FOR_CONFIRMATION)
        new_state = c.handle_event(TradeEvent.CONFIRMED)
        self.assertEqual(new_state, TradeState.FINAL_SAFETY_CHECK)
        self.assertNotEqual(new_state, TradeState.EXECUTING)

    def test_cannot_execute_directly_from_confirmation(self):
        c = TradeConversation(state=TradeState.WAITING_FOR_CONFIRMATION)
        c.handle_event(TradeEvent.CONFIRMED)  # -> FINAL_SAFETY_CHECK
        # Attempting to jump straight to EXECUTION_RESULT_RECEIVED (skipping
        # the pass/fail of the safety check) must be rejected.
        with self.assertRaises(InvalidTradeStateTransition):
            c.handle_event(TradeEvent.EXECUTION_RESULT_RECEIVED)

    def test_trade_intent_rejected_when_decision_was_not_actionable(self):
        c = TradeConversation(state=TradeState.ANALYSIS_READY)
        c.set_analysis_result(decision_actionable=False)
        with self.assertRaises(InvalidTradeStateTransition):
            c.handle_event(TradeEvent.TRADE_INTENT)


class TestTradeStateMachineOverrideFlow(unittest.TestCase):
    """WAIT/HOLD: must pass through the override gate."""

    def test_override_requested_then_accepted_leads_to_amount(self):
        c = TradeConversation(state=TradeState.ANALYSIS_READY)
        c.set_analysis_result(decision_actionable=False)
        self.assertEqual(c.handle_event(TradeEvent.OVERRIDE_REQUESTED), TradeState.OVERRIDE_REQUIRED)
        self.assertEqual(c.handle_event(TradeEvent.OVERRIDE_ACCEPTED), TradeState.WAITING_FOR_AMOUNT)

    def test_override_declined_cancels(self):
        c = TradeConversation(state=TradeState.ANALYSIS_READY)
        c.set_analysis_result(decision_actionable=False)
        c.handle_event(TradeEvent.OVERRIDE_REQUESTED)
        self.assertEqual(c.handle_event(TradeEvent.OVERRIDE_DECLINED), TradeState.CANCELLED)

    def test_override_requested_rejected_when_decision_was_actionable(self):
        c = TradeConversation(state=TradeState.ANALYSIS_READY)
        c.set_analysis_result(decision_actionable=True)
        with self.assertRaises(InvalidTradeStateTransition):
            c.handle_event(TradeEvent.OVERRIDE_REQUESTED)

    def test_two_confirmations_remain_distinct(self):
        # Override confirmation ("Trading anyway?") and the final trade
        # confirmation ("Confirm this trade?") are two separate gates.
        c = TradeConversation(state=TradeState.ANALYSIS_READY)
        c.set_analysis_result(decision_actionable=False)
        c.handle_event(TradeEvent.OVERRIDE_REQUESTED)      # confirmation #1 gate opens
        c.handle_event(TradeEvent.OVERRIDE_ACCEPTED)        # confirmation #1 accepted
        c.handle_event(TradeEvent.AMOUNT_PROVIDED)
        c.handle_event(TradeEvent.PREVIEW_PRESENTED)
        # confirmation #2 gate: still requires its own explicit CONFIRMED event
        with self.assertRaises(InvalidTradeStateTransition):
            c.handle_event(TradeEvent.OVERRIDE_ACCEPTED)  # cannot reuse override acceptance as trade confirmation
        self.assertEqual(c.handle_event(TradeEvent.CONFIRMED), TradeState.FINAL_SAFETY_CHECK)

    def test_cannot_bypass_override_gate_straight_to_amount(self):
        c = TradeConversation(state=TradeState.ANALYSIS_READY)
        c.set_analysis_result(decision_actionable=False)
        with self.assertRaises(InvalidTradeStateTransition):
            c.handle_event(TradeEvent.TRADE_INTENT)


class TestTradeStateMachineHardBlock(unittest.TestCase):

    def test_hard_block_from_analysis_ready(self):
        c = TradeConversation(state=TradeState.ANALYSIS_READY)
        self.assertEqual(c.handle_event(TradeEvent.HARD_BLOCK_DETECTED), TradeState.BLOCKED)

    def test_hard_block_from_waiting_for_amount(self):
        c = TradeConversation(state=TradeState.WAITING_FOR_AMOUNT)
        self.assertEqual(c.handle_event(TradeEvent.HARD_BLOCK_DETECTED), TradeState.BLOCKED)

    def test_hard_block_from_final_safety_check_stale_confirmation(self):
        # Simulates: user confirmed, but the fresh (snapshot #2) safety
        # check finds a new violation. The earlier confirmation must not
        # be treated as still valid.
        c = TradeConversation(state=TradeState.FINAL_SAFETY_CHECK)
        self.assertEqual(c.handle_event(TradeEvent.HARD_BLOCK_DETECTED), TradeState.BLOCKED)

    def test_blocked_state_has_no_execution_path(self):
        c = TradeConversation(state=TradeState.BLOCKED)
        for event in (
            TradeEvent.CONFIRMED,
            TradeEvent.SAFETY_CHECK_PASSED,
            TradeEvent.OVERRIDE_ACCEPTED,
            TradeEvent.TRADE_INTENT,
        ):
            with self.subTest(event=event):
                with self.assertRaises(InvalidTradeStateTransition):
                    c.handle_event(event)

    def test_blocked_has_no_override_path(self):
        # Hard blocks are never overrideable, unlike WAIT/HOLD.
        c = TradeConversation(state=TradeState.BLOCKED)
        with self.assertRaises(InvalidTradeStateTransition):
            c.handle_event(TradeEvent.OVERRIDE_REQUESTED)


class TestTradeStateMachineVerificationAndCancellation(unittest.TestCase):

    def test_verification_failed_is_distinct_terminal_state(self):
        c = TradeConversation(state=TradeState.VERIFYING)
        self.assertEqual(c.handle_event(TradeEvent.VERIFICATION_FAILED), TradeState.VERIFICATION_FAILED)

    def test_verification_failed_has_no_further_execution_path(self):
        c = TradeConversation(state=TradeState.VERIFICATION_FAILED)
        with self.assertRaises(InvalidTradeStateTransition):
            c.handle_event(TradeEvent.CONFIRMED)

    def test_cancelled_trade_cannot_execute(self):
        c = TradeConversation(state=TradeState.CANCELLED)
        with self.assertRaises(InvalidTradeStateTransition):
            c.handle_event(TradeEvent.CONFIRMED)
        with self.assertRaises(InvalidTradeStateTransition):
            c.handle_event(TradeEvent.SAFETY_CHECK_PASSED)

    def test_decline_from_preview_ready_cancels(self):
        c = TradeConversation(state=TradeState.PREVIEW_READY)
        self.assertEqual(c.handle_event(TradeEvent.DECLINED), TradeState.CANCELLED)

    def test_decline_from_waiting_for_confirmation_cancels(self):
        c = TradeConversation(state=TradeState.WAITING_FOR_CONFIRMATION)
        self.assertEqual(c.handle_event(TradeEvent.DECLINED), TradeState.CANCELLED)

    def test_reset_returns_to_idle_from_any_state(self):
        for state in TradeState:
            with self.subTest(state=state):
                c = TradeConversation(state=state)
                self.assertEqual(c.handle_event(TradeEvent.RESET), TradeState.IDLE)

    def test_state_unchanged_after_invalid_event(self):
        c = TradeConversation(state=TradeState.ANALYSIS_READY)
        c.set_analysis_result(decision_actionable=True)
        with self.assertRaises(InvalidTradeStateTransition):
            c.handle_event(TradeEvent.CONFIRMED)
        self.assertEqual(c.state, TradeState.ANALYSIS_READY)


if __name__ == "__main__":
    unittest.main()
