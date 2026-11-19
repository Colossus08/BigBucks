from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from app.engine.money import round_dollars
from app.engine.tax import TaxTable, estimate_annual_tax

PayFrequency = Literal["weekly", "fortnightly", "monthly"]

PERIODS_PER_YEAR: dict[PayFrequency, Decimal] = {
    "weekly": Decimal("52"),
    "fortnightly": Decimal("26"),
    "monthly": Decimal("12"),
}


@dataclass(frozen=True)
class PeriodIncome:
    pay_frequency: PayFrequency
    periods_per_year: int
    gross_annual: Decimal
    gross_period: Decimal
    income_tax_period: Decimal
    medicare_levy_period: Decimal
    total_tax_period: Decimal
    net_period: Decimal
    super_annual: Decimal
    super_period: Decimal


def net_per_period(
    gross_annual: Decimal,
    freq: PayFrequency,
    rates: TaxTable,
    super_rate: Decimal = Decimal("0.12"),
) -> PeriodIncome:
    """Calculate estimated gross, tax, net take-home, and super per pay period."""
    divisor = PERIODS_PER_YEAR[freq]
    annual_tax = estimate_annual_tax(gross_annual, rates)

    gross_period = round_dollars(gross_annual / divisor)
    income_tax_period = round_dollars(annual_tax.income_tax / divisor)
    medicare_period = round_dollars(annual_tax.medicare_levy / divisor)
    total_tax_period = income_tax_period + medicare_period
    net_period = round_dollars(gross_period - total_tax_period)

    super_annual = round_dollars(gross_annual * super_rate)
    super_period = round_dollars(super_annual / divisor)

    return PeriodIncome(
        pay_frequency=freq,
        periods_per_year=int(divisor),
        gross_annual=round_dollars(gross_annual),
        gross_period=gross_period,
        income_tax_period=income_tax_period,
        medicare_levy_period=medicare_period,
        total_tax_period=total_tax_period,
        net_period=net_period,
        super_annual=super_annual,
        super_period=super_period,
    )
