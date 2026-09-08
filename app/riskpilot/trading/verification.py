"""
Trading execution verification.

Reuses the existing Phase 1-16 verify_execution function unmodified —
this module does not reimplement verification logic, it only applies
the existing generic verifier to a trade's expected vs. actual filled
allocation.
"""

from riskpilot.verification.verifier import verify_execution, VerificationResult


def verify_trade_execution(
    symbol: str,
    expected_quote_amount: float,
    actual_quote_amount: float,
    tolerance: float = 0.01,
) -> VerificationResult:
    return verify_execution(
        symbol=symbol,
        expected_value=expected_quote_amount,
        actual_value=actual_quote_amount,
        tolerance=tolerance,
    )
