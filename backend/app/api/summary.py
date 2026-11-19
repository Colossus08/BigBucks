from calendar import monthrange
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.db import get_db
from app.engine.budgeting import _to_period_cents
from app.engine.goals import contribution_to_fortnightly_cents
from app.engine.insights import cadence_to_monthly_cents
from app.engine.summary import TransactionRecord, summarise
from app.models.finance import (
    Account,
    Category,
    FinancialGoal,
    IncomeProfile,
    RecurringPayment,
    Transaction,
)
from app.schemas.finance import CategorySpendOut, MonthlyTrendPoint, SummaryOut
from app.services.categoriser import reconcile_rent_transactions
from app.services.savings import net_moved_by_account_id

router = APIRouter(prefix="/api/summary", tags=["summary"])


def _month_bounds(anchor: date) -> tuple[date, date]:
    last_day = monthrange(anchor.year, anchor.month)[1]
    return date(anchor.year, anchor.month, 1), date(anchor.year, anchor.month, last_day)


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    total = year * 12 + (month - 1) + delta
    return total // 12, (total % 12) + 1


def _to_records(rows: list[Transaction]) -> list[TransactionRecord]:
    return [
        TransactionRecord(
            tx_date=tx.date,
            amount_cents=tx.amount_cents,
            category_id=tx.category_id,
            category_name=tx.category.name if tx.category else "Uncategorised",
            category_group=tx.category.group if tx.category else "Other",
            is_transfer=tx.is_transfer,
            kind=tx.kind,
        )
        for tx in rows
    ]


@router.get("", response_model=SummaryOut)
def get_summary(
    period: str = Query(default="month"),
    anchor_date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
) -> SummaryOut:
    if reconcile_rent_transactions(db) > 0:
        db.commit()
    # Default anchor: latest transaction month if any exist, otherwise today
    if anchor_date is None:
        latest_tx_date = db.scalar(select(Transaction.date).order_by(Transaction.date.desc()).limit(1))
        anchor_date = latest_tx_date or date.today()

    if period == "all":
        start_date = date(2000, 1, 1)
        end_date = date(2099, 12, 31)
    elif period == "year":
        start_date = date(anchor_date.year, 1, 1)
        end_date = date(anchor_date.year, 12, 31)
    else:
        start_date, end_date = _month_bounds(anchor_date)

    tx_rows = list(
        db.scalars(
            select(Transaction)
            .options(joinedload(Transaction.category))
            .where(Transaction.date >= start_date, Transaction.date <= end_date)
        ).all()
    )
    result = summarise(_to_records(tx_rows), start_date=start_date, end_date=end_date)

    accounts = db.scalars(select(Account).where(Account.is_own.is_(True))).all()
    bank_balance_cents = sum(
        a.current_balance_cents for a in accounts if a.type == "transaction"
    )

    profile = db.scalar(select(IncomeProfile))
    pay_freq = profile.pay_frequency if profile else settings.pay_frequency
    rec_rows = db.scalars(select(RecurringPayment)).all()
    recurring_monthly_cents = sum(
        cadence_to_monthly_cents(r.amount_cents, r.cadence) for r in rec_rows
    )
    upcoming_bills_cents = _to_period_cents(recurring_monthly_cents, pay_freq)

    goals = db.scalars(select(FinancialGoal)).all()
    fortnightly_goals = sum(
        contribution_to_fortnightly_cents(g.planned_contribution_cents, g.contribution_frequency)
        for g in goals
    )
    planned_goals_cents = _to_period_cents(round(fortnightly_goals * 26 / 12), pay_freq)

    # Calculate days until next payday from latest Salary deposit (or cycle default)
    cycle_days = 7 if pay_freq == "weekly" else 30 if pay_freq == "monthly" else 14
    salary_cat_id = db.scalar(select(Category.id).where(Category.name == "Salary"))
    last_salary_date = None
    if salary_cat_id is not None:
        last_salary_date = db.scalar(
            select(Transaction.date)
            .where(Transaction.category_id == salary_cat_id, Transaction.amount_cents > 0)
            .order_by(Transaction.date.desc())
            .limit(1)
        )
    if last_salary_date is not None:
        elapsed = max(0, (anchor_date - last_salary_date).days) % cycle_days
        days_until_payday = max(1, cycle_days - elapsed)
    else:
        days_until_payday = cycle_days

    available_to_spend_cents = max(0, bank_balance_cents - upcoming_bills_cents)
    safe_to_spend_cents = max(0, bank_balance_cents - upcoming_bills_cents - planned_goals_cents)
    daily_burn_rate_cents = safe_to_spend_cents // max(1, days_until_payday)

    moved_to_savings_cents = sum(net_moved_by_account_id(db, start_date, end_date).values())

    return SummaryOut(
        period=period,
        start_date=start_date,
        end_date=end_date,
        bank_balance_cents=bank_balance_cents,
        upcoming_bills_cents=upcoming_bills_cents,
        planned_goals_cents=planned_goals_cents,
        safe_to_spend_cents=safe_to_spend_cents,
        days_until_payday=days_until_payday,
        daily_burn_rate_cents=daily_burn_rate_cents,
        available_to_spend_cents=available_to_spend_cents,
        income_cents=result.income_cents,
        gross_expenses_cents=result.gross_expenses_cents,
        refunds_cents=result.refunds_cents,
        reimbursements_cents=result.reimbursements_cents,
        unclassified_in_cents=result.unclassified_in_cents,
        expenses_cents=result.expenses_cents,
        moved_to_savings_cents=moved_to_savings_cents,
        net_savings_cents=result.net_savings_cents,
        savings_rate_pct=result.savings_rate_pct,
        uncategorised_count=result.uncategorised_count,
        by_group=result.by_group,
        by_category=[
            CategorySpendOut(
                category_id=item.category_id,
                category_name=item.category_name,
                category_group=item.category_group,
                total_cents=item.total_cents,
            )
            for item in result.by_category
        ],
    )


@router.get("/months", response_model=list[str])
def list_available_months(db: Session = Depends(get_db)) -> list[str]:
    dates = db.scalars(select(Transaction.date).order_by(Transaction.date.desc())).all()
    seen: list[str] = []
    seen_set: set[str] = set()
    for d in dates:
        ym = f"{d.year:04d}-{d.month:02d}"
        if ym not in seen_set:
            seen_set.add(ym)
            seen.append(ym)
    return seen


@router.get("/trend", response_model=list[MonthlyTrendPoint])
def get_monthly_trend(
    months: int = Query(default=6, ge=1, le=24),
    anchor_date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
) -> list[MonthlyTrendPoint]:
    if anchor_date is None:
        latest_tx_date = db.scalar(select(Transaction.date).order_by(Transaction.date.desc()).limit(1))
        anchor_date = latest_tx_date or date.today()

    tx_rows = list(
        db.scalars(select(Transaction).options(joinedload(Transaction.category))).all()
    )
    records = _to_records(tx_rows)

    points: list[MonthlyTrendPoint] = []
    for offset in range(-(months - 1), 1):
        y, m = _shift_month(anchor_date.year, anchor_date.month, offset)
        start, end = _month_bounds(date(y, m, 1))
        res = summarise(records, start_date=start, end_date=end)
        points.append(
            MonthlyTrendPoint(
                month=f"{y:04d}-{m:02d}",
                income_cents=res.income_cents,
                expenses_cents=res.expenses_cents,
                net_savings_cents=res.net_savings_cents,
            )
        )
    return points
