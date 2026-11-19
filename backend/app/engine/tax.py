from dataclasses import dataclass
from decimal import Decimal
import json
from pathlib import Path

from app.engine.money import round_dollars


@dataclass(frozen=True)
class TaxBracket:
    min_income: Decimal
    max_income: Decimal | None
    rate: Decimal
    base_tax: Decimal


@dataclass(frozen=True)
class TaxTable:
    tax_year: str
    medicare_levy_rate: Decimal
    brackets: tuple[TaxBracket, ...]


@dataclass(frozen=True)
class TaxBreakdown:
    gross_annual: Decimal
    income_tax: Decimal
    medicare_levy: Decimal
    total_tax: Decimal
    net_annual: Decimal


DEFAULT_RATES_PATH = Path(__file__).resolve().parent.parent / "data" / "tax_rates_2026_27.json"


def load_tax_table(path: Path = DEFAULT_RATES_PATH) -> TaxTable:
    """Load ATO tax brackets and Medicare levy rate from JSON."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    brackets = tuple(
        TaxBracket(
            min_income=Decimal(b["min"]),
            max_income=Decimal(b["max"]) if b["max"] is not None else None,
            rate=Decimal(b["rate"]),
            base_tax=Decimal(b["base_tax"]),
        )
        for b in raw["brackets"]
    )
    return TaxTable(
        tax_year=raw["tax_year"],
        medicare_levy_rate=Decimal(raw["medicare_levy_rate"]),
        brackets=brackets,
    )


def estimate_annual_tax(gross: Decimal, rates: TaxTable) -> TaxBreakdown:
    """Estimate annual Australian resident income tax and Medicare levy."""
    if gross <= Decimal("0"):
        zero = Decimal("0.00")
        return TaxBreakdown(zero, zero, zero, zero, zero)

    income_tax = Decimal("0.00")
    for bracket in rates.brackets:
        in_lower = gross > bracket.min_income
        in_upper = bracket.max_income is None or gross <= bracket.max_income
        if in_lower and in_upper:
            income_tax = bracket.base_tax + (gross - bracket.min_income) * bracket.rate
            break

    income_tax = round_dollars(income_tax)
    medicare_levy = round_dollars(gross * rates.medicare_levy_rate)
    total_tax = income_tax + medicare_levy
    net_annual = round_dollars(gross - total_tax)

    return TaxBreakdown(
        gross_annual=round_dollars(gross),
        income_tax=income_tax,
        medicare_levy=medicare_levy,
        total_tax=total_tax,
        net_annual=net_annual,
    )
