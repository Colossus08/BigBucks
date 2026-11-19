from decimal import Decimal
from app.engine.tax import estimate_annual_tax, load_tax_table


def test_tax_free_threshold_and_brackets() -> None:
    rates = load_tax_table()

    below = estimate_annual_tax(Decimal("18200"), rates)
    assert below.income_tax == Decimal("0.00")
    assert below.medicare_levy == Decimal("364.00")

    b1 = estimate_annual_tax(Decimal("45000"), rates)
    # (45000 - 18200) * 0.16 = 4288.00
    assert b1.income_tax == Decimal("4288.00")

    b2 = estimate_annual_tax(Decimal("135000"), rates)
    # 4288 + (135000 - 45000) * 0.30 = 31288.00
    assert b2.income_tax == Decimal("31288.00")


def test_contract_salary_58193() -> None:
    rates = load_tax_table()
    res = estimate_annual_tax(Decimal("58193"), rates)
    # 4288 + (58193 - 45000) * 0.30 = 4288 + 3957.90 = 8245.90
    assert res.income_tax == Decimal("8245.90")
    # 58193 * 0.02 = 1163.86
    assert res.medicare_levy == Decimal("1163.86")
    assert res.total_tax == Decimal("9409.76")
    assert res.net_annual == Decimal("48783.24")
