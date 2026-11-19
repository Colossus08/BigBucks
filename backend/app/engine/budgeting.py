from calendar import monthrange
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable

from app.engine.summary import TransactionRecord


@dataclass(frozen=True)
class BudgetSpec:
    budget_id: int
    category_id: int
    category_name: str
    category_group: str
    period: str
    limit_cents: int
    name: str = ""


@dataclass(frozen=True)
class BudgetEvaluation:
    budget_id: int
    category_id: int
    category_name: str
    category_group: str
    period: str
    limit_cents: int
    spent_cents: int
    remaining_cents: int
    pct_used: Decimal
    projected_cents: int
    status: str  # ok | warning | over
    name: str = ""


@dataclass(frozen=True)
class BudgetRecommendation:
    category_id: int
    category_name: str
    category_group: str
    avg_monthly_cents: int
    recommended_monthly_cents: int
    reasoning: str


@dataclass(frozen=True)
class PayCycleAllocation:
    pay_frequency: str
    net_period_cents: int
    budgeted_expenses_cents: int
    recurring_bills_cents: int
    goal_contributions_cents: int
    unallocated_cents: int


def _period_bounds(period: str, anchor: date) -> tuple[date, date]:
    if period == "weekly":
        start = anchor - timedelta(days=anchor.weekday())
        return start, start + timedelta(days=6)
    if period == "fortnightly":
        start = anchor - timedelta(days=anchor.weekday() + 7)
        return start, start + timedelta(days=13)
    last_day = monthrange(anchor.year, anchor.month)[1]
    return date(anchor.year, anchor.month, 1), date(anchor.year, anchor.month, last_day)


def _to_monthly_cents(amount_cents: int, period: str) -> int:
    if period == "weekly":
        return round(amount_cents * 52 / 12)
    if period == "fortnightly":
        return round(amount_cents * 26 / 12)
    return amount_cents


def _to_period_cents(monthly_cents: int, pay_frequency: str) -> int:
    if pay_frequency == "weekly":
        return round(monthly_cents * 12 / 52)
    if pay_frequency == "fortnightly":
        return round(monthly_cents * 12 / 26)
    return monthly_cents


def evaluate_budgets(
    budgets: Iterable[BudgetSpec],
    records: Iterable[TransactionRecord],
    anchor: date,
) -> list[BudgetEvaluation]:
    """Evaluate actual spending and end-of-period projection against each budget."""
    record_list = list(records)
    results: list[BudgetEvaluation] = []

    for b in budgets:
        start, end = _period_bounds(b.period, anchor)
        # Refunds (positive amounts in the same category) reduce what counts as spent.
        spent = max(
            0,
            sum(
                -r.amount_cents
                for r in record_list
                if r.kind == "actual"
                and not r.is_transfer
                and r.category_id == b.category_id
                and start <= r.tx_date <= end
            ),
        )
        remaining = b.limit_cents - spent
        pct_used = (
            (Decimal(spent) / Decimal(b.limit_cents) * Decimal("100")).quantize(Decimal("0.1"))
            if b.limit_cents > 0
            else Decimal("0.0")
        )

        total_days = (end - start).days + 1
        elapsed_days = max(1, min(total_days, (anchor - start).days + 1))
        projected = round(spent * total_days / elapsed_days)

        if spent > b.limit_cents:
            status = "over"
        elif pct_used >= Decimal("80.0"):
            status = "warning"
        else:
            status = "ok"

        results.append(
            BudgetEvaluation(
                budget_id=b.budget_id,
                category_id=b.category_id,
                category_name=b.category_name,
                category_group=b.category_group,
                period=b.period,
                limit_cents=b.limit_cents,
                spent_cents=spent,
                remaining_cents=remaining,
                pct_used=pct_used,
                projected_cents=projected,
                status=status,
                name=b.name or b.category_name,
            )
        )

    return sorted(results, key=lambda x: x.pct_used, reverse=True)


def recommend_budgets(
    records: Iterable[TransactionRecord],
    anchor: date,
    months: int = 3,
) -> list[BudgetRecommendation]:
    """Recommend realistic monthly budgets from recent historical spending."""
    cutoff_year = anchor.year
    cutoff_month = anchor.month - (months - 1)
    while cutoff_month <= 0:
        cutoff_month += 12
        cutoff_year -= 1
    start = date(cutoff_year, cutoff_month, 1)

    cat_totals: dict[tuple[int, str, str], int] = defaultdict(int)
    active_months: set[tuple[int, int]] = set()

    for r in records:
        if r.kind != "actual" or r.is_transfer or r.amount_cents >= 0:
            continue
        if r.category_id is None or r.category_name in {"Uncategorised", "Internal transfer"}:
            continue
        if r.tx_date < start or r.tx_date > anchor:
            continue
        active_months.add((r.tx_date.year, r.tx_date.month))
        cat_totals[(r.category_id, r.category_name, r.category_group)] += abs(r.amount_cents)

    divisor = max(1, len(active_months))
    recs: list[BudgetRecommendation] = []
    for (cid, cname, cgroup), total in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True):
        avg_monthly = round(total / divisor)
        # Round up to nearest $10 (1000 cents) for practical budgeting
        recommended = ((avg_monthly + 999) // 1000) * 1000
        recs.append(
            BudgetRecommendation(
                category_id=cid,
                category_name=cname,
                category_group=cgroup,
                avg_monthly_cents=avg_monthly,
                recommended_monthly_cents=recommended,
                reasoning=f"Based on {divisor} month(s) of actual spending averaging ${avg_monthly / 100:,.2f}/mo.",
            )
        )
    return recs


def build_pay_cycle_plan(
    net_period_cents: int,
    pay_frequency: str,
    budgets: Iterable[BudgetSpec],
    goal_contributions_per_period_cents: int,
    recurring_bills_per_period_cents: int = 0,
) -> PayCycleAllocation:
    """Zero-based pay-cycle allocation showing where each pay goes."""
    monthly_budget_total = sum(_to_monthly_cents(b.limit_cents, b.period) for b in budgets)
    budgeted_per_period = _to_period_cents(monthly_budget_total, pay_frequency)
    unallocated = (
        net_period_cents
        - budgeted_per_period
        - recurring_bills_per_period_cents
        - goal_contributions_per_period_cents
    )
    return PayCycleAllocation(
        pay_frequency=pay_frequency,
        net_period_cents=net_period_cents,
        budgeted_expenses_cents=budgeted_per_period,
        recurring_bills_cents=recurring_bills_per_period_cents,
        goal_contributions_cents=goal_contributions_per_period_cents,
        unallocated_cents=unallocated,
    )
