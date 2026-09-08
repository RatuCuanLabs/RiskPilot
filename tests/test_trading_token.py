import unittest

from riskpilot.trading.token import is_supported_token, to_symbol, normalize_token, UnsupportedTokenError


class TestToken(unittest.TestCase):

    def test_supported_token_lowercase(self):
        self.assertTrue(is_supported_token("btc"))

    def test_supported_token_with_whitespace(self):
        self.assertTrue(is_supported_token("  ETH  "))

    def test_unsupported_token(self):
        self.assertFalse(is_supported_token("DOGE"))

    def test_to_symbol_supported(self):
        self.assertEqual(to_symbol("btc"), "BTCUSDT")

    def test_to_symbol_unsupported_raises(self):
        with self.assertRaises(UnsupportedTokenError):
            to_symbol("DOGE")

    def test_normalize_token(self):
        self.assertEqual(normalize_token(" sol "), "SOL")

    def test_empty_token_unsupported(self):
        self.assertFalse(is_supported_token(""))
        self.assertFalse(is_supported_token(None))


if __name__ == "__main__":
    unittest.main()
