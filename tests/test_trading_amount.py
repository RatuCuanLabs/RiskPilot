import unittest

from riskpilot.trading.amount import parse_usdt_amount, InvalidAmountError


class TestAmount(unittest.TestCase):

    def test_plain_number(self):
        self.assertEqual(parse_usdt_amount("50"), 50.0)

    def test_with_usdt_suffix(self):
        self.assertEqual(parse_usdt_amount("50 USDT"), 50.0)

    def test_with_lowercase_suffix_no_space(self):
        self.assertEqual(parse_usdt_amount("50.5usdt"), 50.5)

    def test_zero_raises(self):
        with self.assertRaises(InvalidAmountError):
            parse_usdt_amount("0")

    def test_negative_raises(self):
        with self.assertRaises(InvalidAmountError):
            parse_usdt_amount("-10")

    def test_non_numeric_raises(self):
        with self.assertRaises(InvalidAmountError):
            parse_usdt_amount("a lot")

    def test_none_raises(self):
        with self.assertRaises(InvalidAmountError):
            parse_usdt_amount(None)

    def test_empty_string_raises(self):
        with self.assertRaises(InvalidAmountError):
            parse_usdt_amount("")


if __name__ == "__main__":
    unittest.main()
