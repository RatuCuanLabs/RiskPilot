"""
Allocation amount parsing for the trading conversation.

Deterministic parsing/validation only. Never invents or assumes an
amount — the caller must always pass the user's literal input.
"""

import re

_AMOUNT_PATTERN = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*(usdt)?\s*$", re.IGNORECASE)


class InvalidAmountError(ValueError):
    pass


def parse_usdt_amount(raw_amount: str) -> float:
    """
    Parses a user-supplied allocation string like "50", "50 USDT", "50.5usdt"
    into a positive float. Raises InvalidAmountError for anything else
    (missing, zero, negative, non-numeric, malformed).
    """
    if raw_amount is None:
        raise InvalidAmountError("No allocation amount was provided.")

    match = _AMOUNT_PATTERN.match(raw_amount)
    if not match:
        raise InvalidAmountError(f"Could not parse {raw_amount!r} as a USDT amount.")

    amount = float(match.group(1))
    if amount <= 0:
        raise InvalidAmountError(f"Allocation amount must be positive, got {amount}.")

    return amount
