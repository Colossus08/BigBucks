from decimal import Decimal
from app.engine.income import net_per_period
from app.engine.tax import load_tax_table


def test_pay_frequencies_sum_close_to_annual() -> None:
    rates = load_tax_table()
    gross = Decimal("58193.00")

    for freq, periods in [("weekly", 52), ("fortnightly", 26), ("monthly", 12)]:
        res = net_per_period(gross, freq, rates)  # type: ignore[arg-type]
        assert res.periods_per_year == periods
        assert abs(res.gross_period * periods - gross) < Decimal("1.00")
        assert abs(res.super_period * periods - res.super_annual) < Decimal("1.00")
        assert res.net_period > Decimal("0")
