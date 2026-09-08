"""
Token validation for the trading conversation.

Deterministic, no network calls. This is intentionally conservative: only
a small allowlist of USDT-quoted spot symbols is considered supported for
this vertical slice. Expanding the allowlist is a deliberate later step,
not something inferred from user input.
"""

from typing import FrozenSet

SUPPORTED_BASE_TOKENS: FrozenSet[str] = frozenset({"BTC", "ETH", "BNB", "SOL"})


class UnsupportedTokenError(ValueError):
    pass


def normalize_token(raw_token: str) -> str:
    return (raw_token or "").strip().upper()


def is_supported_token(raw_token: str) -> bool:
    return normalize_token(raw_token) in SUPPORTED_BASE_TOKENS


def to_symbol(raw_token: str, quote: str = "USDT") -> str:
    """
    Returns the trading symbol for a supported token, e.g. "BTC" -> "BTCUSDT".
    Raises UnsupportedTokenError if the token is not in the allowlist.
    """
    token = normalize_token(raw_token)
    if token not in SUPPORTED_BASE_TOKENS:
        raise UnsupportedTokenError(
            f"{raw_token!r} is not a supported token. Supported: {sorted(SUPPORTED_BASE_TOKENS)}"
        )
    return f"{token}{quote.upper()}"
