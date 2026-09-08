import unittest

from riskpilot.leverage.types import MarketType, RiskStatus, TradeIntent
from riskpilot.leverage.snapshot import LeverageMarketSnapshot
from riskpilot.leverage.engine import LeverageRiskEngine


def _snap(market_type, current=None, post_trade=None, **kwargs):
    return LeverageMarketSnapshot(
        market_type=market_type,
        current_risk_status=current,
        post_trade_risk_status=post_trade,
        **kwargs,
    )


class TestMarketTypeSupport(unittest.TestCase):

    def test_spot_is_not_applicable(self):
        result = LeverageRiskEngine.evaluate(_snap(MarketType.SPOT), TradeIntent.OPEN)
        self.assertEqual(result.risk_status, RiskStatus.NOT_APPLICABLE)
        self.assertFalse(result.hard_block)

    def test_spot_never_reports_leverage_values(self):
        # Even if leverage-looking fields are (incorrectly) supplied for SPOT,
        # the engine must not surface invented leverage data for SPOT.
        snap = _snap(MarketType.SPOT, leverage=10, liquidation_price=100.0, mark_price=105.0)
        result = LeverageRiskEngine.evaluate(snap, TradeIntent.OPEN)
        self.assertIsNone(result.leverage)
        self.assertIsNone(result.liquidation_price)
        self.assertIsNone(result.liquidation_distance)

    def test_margin_spot_is_evaluated(self):
        result = LeverageRiskEngine.evaluate(
            _snap(MarketType.MARGIN_SPOT, current=RiskStatus.LOW, post_trade=RiskStatus.LOW),
            TradeIntent.OPEN,
        )
        self.assertEqual(result.risk_status, RiskStatus.LOW)

    def test_usd_m_futures_is_evaluated(self):
        result = LeverageRiskEngine.evaluate(
            _snap(MarketType.USD_M_FUTURES, current=RiskStatus.LOW, post_trade=RiskStatus.WARNING),
            TradeIntent.OPEN,
        )
        self.assertEqual(result.risk_status, RiskStatus.WARNING)

    def test_coin_m_futures_is_evaluated(self):
        result = LeverageRiskEngine.evaluate(
            _snap(MarketType.COIN_M_FUTURES, current=RiskStatus.LOW, post_trade=RiskStatus.WARNING),
            TradeIntent.OPEN,
        )
        self.assertEqual(result.risk_status, RiskStatus.WARNING)


class TestRiskStatuses(unittest.TestCase):

    def test_low(self):
        result = LeverageRiskEngine.evaluate(
            _snap(MarketType.USD_M_FUTURES, current=RiskStatus.LOW, post_trade=RiskStatus.LOW),
            TradeIntent.OPEN,
        )
        self.assertEqual(result.risk_status, RiskStatus.LOW)
        self.assertFalse(result.hard_block)

    def test_warning(self):
        result = LeverageRiskEngine.evaluate(
            _snap(MarketType.USD_M_FUTURES, current=RiskStatus.LOW, post_trade=RiskStatus.WARNING),
            TradeIntent.OPEN,
        )
        self.assertEqual(result.risk_status, RiskStatus.WARNING)
        self.assertFalse(result.hard_block)
        self.assertTrue(result.mitigation_required)

    def test_critical(self):
        result = LeverageRiskEngine.evaluate(
            _snap(MarketType.USD_M_FUTURES, current=RiskStatus.WARNING, post_trade=RiskStatus.CRITICAL),
            TradeIntent.OPEN,
        )
        self.assertEqual(result.risk_status, RiskStatus.CRITICAL)
        self.assertTrue(result.hard_block)

    def test_unknown(self):
        result = LeverageRiskEngine.evaluate(
            _snap(MarketType.USD_M_FUTURES, current=RiskStatus.LOW, post_trade=None),
            TradeIntent.OPEN,
        )
        self.assertEqual(result.risk_status, RiskStatus.UNKNOWN)
        self.assertTrue(result.hard_block)

    def test_not_applicable(self):
        result = LeverageRiskEngine.evaluate(_snap(MarketType.SPOT), TradeIntent.OPEN)
        self.assertEqual(result.risk_status, RiskStatus.NOT_APPLICABLE)


class TestHardBlockForRiskIncreasingIntents(unittest.TestCase):

    def test_critical_open_hard_blocks(self):
        result = LeverageRiskEngine.evaluate(
            _snap(MarketType.USD_M_FUTURES, post_trade=RiskStatus.CRITICAL), TradeIntent.OPEN
        )
        self.assertTrue(result.hard_block)
        self.assertFalse(result.override_allowed)

    def test_critical_add_hard_blocks(self):
        result = LeverageRiskEngine.evaluate(
            _snap(MarketType.USD_M_FUTURES, post_trade=RiskStatus.CRITICAL), TradeIntent.ADD
        )
        self.assertTrue(result.hard_block)
        self.assertFalse(result.override_allowed)

    def test_unknown_open_hard_blocks(self):
        result = LeverageRiskEngine.evaluate(
            _snap(MarketType.USD_M_FUTURES, post_trade=None), TradeIntent.OPEN
        )
        self.assertTrue(result.hard_block)
        self.assertFalse(result.override_allowed)

    def test_unknown_add_hard_blocks(self):
        result = LeverageRiskEngine.evaluate(
            _snap(MarketType.USD_M_FUTURES, post_trade=None), TradeIntent.ADD
        )
        self.assertTrue(result.hard_block)
        self.assertFalse(result.override_allowed)

    def test_hedge_with_unknown_post_trade_hard_blocks(self):
        # HEDGE must not be automatically treated as safe.
        result = LeverageRiskEngine.evaluate(
            _snap(MarketType.USD_M_FUTURES, post_trade=None), TradeIntent.HEDGE
        )
        self.assertTrue(result.hard_block)


class TestRiskReducingActionsExempt(unittest.TestCase):

    def test_critical_reduce_is_allowed(self):
        result = LeverageRiskEngine.evaluate(
            _snap(MarketType.USD_M_FUTURES, current=RiskStatus.CRITICAL), TradeIntent.REDUCE
        )
        self.assertFalse(result.hard_block)

    def test_critical_close_is_allowed(self):
        result = LeverageRiskEngine.evaluate(
            _snap(MarketType.USD_M_FUTURES, current=RiskStatus.CRITICAL), TradeIntent.CLOSE
        )
        self.assertFalse(result.hard_block)

    def test_unknown_reduce_is_still_allowed(self):
        result = LeverageRiskEngine.evaluate(
            _snap(MarketType.USD_M_FUTURES, current=None), TradeIntent.REDUCE
        )
        self.assertFalse(result.hard_block)


class TestPostTradeSimulation(unittest.TestCase):

    def test_current_low_projected_warning(self):
        result = LeverageRiskEngine.evaluate(
            _snap(MarketType.USD_M_FUTURES, current=RiskStatus.LOW, post_trade=RiskStatus.WARNING),
            TradeIntent.ADD,
        )
        self.assertEqual(result.current_risk_status, RiskStatus.LOW)
        self.assertEqual(result.post_trade_risk, RiskStatus.WARNING)
        self.assertEqual(result.risk_status, RiskStatus.WARNING)

    def test_current_warning_projected_critical(self):
        result = LeverageRiskEngine.evaluate(
            _snap(MarketType.USD_M_FUTURES, current=RiskStatus.WARNING, post_trade=RiskStatus.CRITICAL),
            TradeIntent.ADD,
        )
        self.assertEqual(result.risk_status, RiskStatus.CRITICAL)
        self.assertTrue(result.hard_block)

    def test_current_critical_remains_critical(self):
        result = LeverageRiskEngine.evaluate(
            _snap(MarketType.USD_M_FUTURES, current=RiskStatus.CRITICAL, post_trade=RiskStatus.CRITICAL),
            TradeIntent.ADD,
        )
        self.assertEqual(result.risk_status, RiskStatus.CRITICAL)

    def test_missing_post_trade_data_is_unknown_for_open(self):
        result = LeverageRiskEngine.evaluate(
            _snap(MarketType.USD_M_FUTURES, current=RiskStatus.LOW, post_trade=None),
            TradeIntent.OPEN,
        )
        self.assertEqual(result.risk_status, RiskStatus.UNKNOWN)
        self.assertTrue(result.hard_block)


class TestDataIntegrity(unittest.TestCase):

    def test_missing_liquidation_price_handled_honestly(self):
        result = LeverageRiskEngine.evaluate(
            _snap(MarketType.USD_M_FUTURES, current=RiskStatus.LOW, post_trade=RiskStatus.LOW, mark_price=100.0),
            TradeIntent.OPEN,
        )
        self.assertIsNone(result.liquidation_price)
        self.assertIsNone(result.liquidation_distance)

    def test_missing_maintenance_margin_handled_honestly(self):
        result = LeverageRiskEngine.evaluate(
            _snap(MarketType.USD_M_FUTURES, current=RiskStatus.LOW, post_trade=RiskStatus.LOW),
            TradeIntent.OPEN,
        )
        self.assertIsNone(result.maintenance_margin)

    def test_missing_available_margin_handled_honestly(self):
        result = LeverageRiskEngine.evaluate(
            _snap(MarketType.USD_M_FUTURES, current=RiskStatus.LOW, post_trade=RiskStatus.LOW),
            TradeIntent.OPEN,
        )
        self.assertIsNone(result.available_margin)

    def test_liquidation_distance_is_plain_subtraction_not_invented(self):
        result = LeverageRiskEngine.evaluate(
            _snap(
                MarketType.USD_M_FUTURES,
                current=RiskStatus.LOW,
                post_trade=RiskStatus.WARNING,
                mark_price=105000.00,
                liquidation_price=102500.00,
            ),
            TradeIntent.OPEN,
        )
        self.assertAlmostEqual(result.liquidation_distance, 2500.00)

    def test_no_liquidation_distance_invented_when_prices_missing(self):
        result = LeverageRiskEngine.evaluate(
            _snap(MarketType.USD_M_FUTURES, current=RiskStatus.LOW, post_trade=RiskStatus.LOW),
            TradeIntent.OPEN,
        )
        self.assertIsNone(result.liquidation_distance)

    def test_structured_result_matches_spec_shape(self):
        result = LeverageRiskEngine.evaluate(
            _snap(
                MarketType.USD_M_FUTURES,
                current=RiskStatus.LOW,
                post_trade=RiskStatus.WARNING,
                leverage=10,
                margin_used=125.50,
                available_margin=300.00,
                maintenance_margin=18.20,
                liquidation_price=102500.00,
                mark_price=105000.00,
            ),
            TradeIntent.OPEN,
        )
        d = result.as_dict()
        for key in (
            "market_type", "risk_status", "leverage", "margin_used", "available_margin",
            "maintenance_margin", "liquidation_price", "mark_price", "liquidation_distance",
            "hard_block", "mitigation",
        ):
            self.assertIn(key, d)
        self.assertEqual(d["mitigation"], {"required": True})


if __name__ == "__main__":
    unittest.main()
