from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")
HUNDRED = Decimal("100")


def to_cents(amount: Decimal | str | int | float) -> int:
    """Convert a dollar amount to integer cents using half-up rounding."""
    dec = amount if isinstance(amount, Decimal) else Decimal(str(amount))
    return int((dec * HUNDRED).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def from_cents(cents: int) -> Decimal:
    """Convert integer cents to a 2-decimal-place Decimal."""
    return (Decimal(cents) / HUNDRED).quantize(CENT, rounding=ROUND_HALF_UP)


def round_dollars(amount: Decimal) -> Decimal:
    """Round a Decimal to 2 decimal places."""
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)
