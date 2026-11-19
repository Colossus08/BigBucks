from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable


@dataclass(frozen=True)
class TransactionRecord:
    tx_date: date
    amount_cents: int
    category_id: int | None
    category_name: str
    category_group: str
    is_transfer: bool
    kind: str = "actual"


@dataclass(frozen=True)
class CategoryBreakdownItem:
    category_id: int | None
    category_name: str
    category_group: str
    total_cents: int


@dataclass(frozen=True)
class SummaryResult:
    income_cents: int
    gross_expenses_cents: int  # spending net of refunds, before reimbursements
    refunds_cents: int
    reimbursements_cents: int
    unclassified_in_cents: int  # money in that has no category yet (not counted as income)
    expenses_cents: int  # gross_expenses minus reimbursements
    net_savings_cents: int
    savings_rate_pct: Decimal
    uncategorised_count: int
    by_group: dict[str, int]
    by_category: list[CategoryBreakdownItem]


# Groups whose positive amounts are treated as real income.
_INCOME_GROUPS = {"Income"}
# Groups that are never an expense (positive amounts here are not refunds).
_NON_EXPENSE_GROUPS = {"Income", "Reimbursements", "Transfer", "Other"}


def summarise(
    records: Iterable[TransactionRecord],
    start_date: date | None = None,
    end_date: date | None = None,
) -> SummaryResult:
    """Aggregate income, expenses, savings and category totals.

    Rules for money coming in (positive amounts):
    - category group "Income"          -> income
    - category group "Reimbursements"  -> offsets spending (someone paying you back)
    - an expense category (e.g. Groceries, Subscriptions) -> a refund that reduces that category
    - uncategorised                    -> held in `unclassified_in_cents`, NOT counted as income,
                                          until you categorise it
    Internal transfers and non-actual records are always excluded.
    """
    income_cents = 0
    spend_cents = 0
    refunds_cents = 0
    reimbursements_cents = 0
    unclassified_in_cents = 0
    uncategorised_count = 0
    by_group: dict[str, int] = defaultdict(int)
    cat_totals: dict[tuple[int | None, str, str], int] = defaultdict(int)

    for rec in records:
        if rec.kind != "actual":
            continue
        if start_date and rec.tx_date < start_date:
            continue
        if end_date and rec.tx_date > end_date:
            continue
        if rec.is_transfer:
            continue

        is_uncategorised = rec.category_id is None or rec.category_name == "Uncategorised"
        if is_uncategorised:
            uncategorised_count += 1

        key = (rec.category_id, rec.category_name, rec.category_group)

        if rec.amount_cents > 0:
            if is_uncategorised:
                unclassified_in_cents += rec.amount_cents
            elif rec.category_group in _INCOME_GROUPS:
                income_cents += rec.amount_cents
            elif rec.category_group == "Reimbursements":
                reimbursements_cents += rec.amount_cents
            elif rec.category_group in _NON_EXPENSE_GROUPS:
                unclassified_in_cents += rec.amount_cents
            else:
                # Refund into an expense category: reduces that category's spend.
                refunds_cents += rec.amount_cents
                by_group[rec.category_group] -= rec.amount_cents
                cat_totals[key] -= rec.amount_cents
        elif rec.amount_cents < 0:
            spent = abs(rec.amount_cents)
            spend_cents += spent
            by_group[rec.category_group] += spent
            cat_totals[key] += spent

    gross_expenses_cents = max(0, spend_cents - refunds_cents)
    expenses_cents = max(0, gross_expenses_cents - reimbursements_cents)
    net_savings_cents = income_cents - expenses_cents
    if income_cents > 0:
        savings_rate_pct = (Decimal(net_savings_cents) / Decimal(income_cents) * Decimal("100")).quantize(
            Decimal("0.1")
        )
    else:
        savings_rate_pct = Decimal("0.0")

    by_category = [
        CategoryBreakdownItem(
            category_id=cid,
            category_name=cname,
            category_group=cgroup,
            total_cents=total,
        )
        for (cid, cname, cgroup), total in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)
        if total > 0
    ]

    return SummaryResult(
        income_cents=income_cents,
        gross_expenses_cents=gross_expenses_cents,
        refunds_cents=refunds_cents,
        reimbursements_cents=reimbursements_cents,
        unclassified_in_cents=unclassified_in_cents,
        expenses_cents=expenses_cents,
        net_savings_cents=net_savings_cents,
        savings_rate_pct=savings_rate_pct,
        uncategorised_count=uncategorised_count,
        by_group={g: v for g, v in sorted(by_group.items(), key=lambda x: x[1], reverse=True) if v > 0},
        by_category=by_category,
    )
