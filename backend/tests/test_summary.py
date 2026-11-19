from datetime import date
from decimal import Decimal
from app.engine.summary import TransactionRecord, summarise


def test_summarise_excludes_transfers_and_calculates_savings_rate() -> None:
    records = [
        TransactionRecord(date(2026, 11, 1), 200000, 10, "Salary", "Income", False),
        TransactionRecord(date(2026, 11, 2), -50000, 1, "Groceries", "Essential", False),
        TransactionRecord(date(2026, 11, 3), -80000, 99, "Internal transfer", "Transfer", True),
        TransactionRecord(date(2026, 11, 4), -10000, None, "Uncategorised", "Other", False),
    ]
    res = summarise(records, date(2026, 11, 1), date(2026, 11, 30))
    assert res.income_cents == 200000
    assert res.expenses_cents == 60000
    assert res.net_savings_cents == 140000
    assert res.savings_rate_pct == Decimal("70.0")
    assert res.uncategorised_count == 1
    assert res.by_group["Essential"] == 50000


def test_summarise_empty_month_returns_zeros() -> None:
    res = summarise([], date(2026, 10, 1), date(2026, 10, 31))
    assert res.income_cents == 0
    assert res.expenses_cents == 0
    assert res.net_savings_cents == 0
    assert res.savings_rate_pct == Decimal("0.0")


def test_reimbursements_offset_expenses_not_income() -> None:
    records = [
        TransactionRecord(date(2026, 11, 1), 200000, 10, "Salary", "Income", False),
        TransactionRecord(date(2026, 11, 2), -10000, 1, "Restaurants", "Lifestyle", False),
        TransactionRecord(date(2026, 11, 3), 5000, 11, "Reimbursements", "Reimbursements", False),
    ]
    res = summarise(records, date(2026, 11, 1), date(2026, 11, 30))
    assert res.income_cents == 200000
    assert res.expenses_cents == 5000
    assert res.net_savings_cents == 195000
