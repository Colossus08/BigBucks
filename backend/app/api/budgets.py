from calendar import monthrange
from collections import defaultdict
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.summary import _month_bounds, _to_records
from app.config import settings
from app.db import get_db
from app.engine.budgeting import (
    BudgetSpec,
    _to_monthly_cents,
    _to_period_cents,
    build_pay_cycle_plan,
    evaluate_budgets,
    recommend_budgets,
)
from app.engine.goals import contribution_to_fortnightly_cents
from app.engine.income import PayFrequency, net_per_period
from app.engine.insights import cadence_to_monthly_cents
from app.engine.money import from_cents, to_cents
from app.engine.tax import load_tax_table
from app.models.finance import (
    Budget,
    Category,
    FinancialGoal,
    IncomeProfile,
    RecurringPayment,
    Transaction,
)
from app.schemas.finance import (
    BudgetCreate,
    BudgetEvalOut,
    BudgetRecommendationOut,
    BudgetUpdate,
    CategoryHistoricalSpendOut,
    NetPayUpdate,
    PayCyclePlanOut,
)

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


def _anchor_date(db: Session) -> date:
    latest = db.scalar(select(Transaction.date).order_by(Transaction.date.desc()).limit(1))
    return latest or date.today()


def _load_specs(db: Session) -> list[BudgetSpec]:
    rows = db.scalars(
        select(Budget).options(joinedload(Budget.category)).where(Budget.is_active.is_(True))
    ).all()
    return [
        BudgetSpec(
            budget_id=b.id,
            category_id=b.category_id,
            category_name=b.category.name if b.category else "Unknown",
            category_group=b.category.group if b.category else "Other",
            period=b.period,
            limit_cents=b.limit_cents,
            name=(b.name.strip() if b.name and b.name.strip() else (b.category.name if b.category else "Unknown")),
        )
        for b in rows
    ]


def _resolve_month_anchor(db: Session, month: str | None) -> date:
    if not month:
        return _anchor_date(db)
    try:
        parts = month.strip().split("-")
        if len(parts) != 2:
            raise ValueError("Expected YYYY-MM")
        year = int(parts[0])
        m = int(parts[1])
        last_day = monthrange(year, m)[1]
        return date(year, m, last_day)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid month format; expected YYYY-MM") from exc


@router.get("", response_model=list[BudgetEvalOut])
def list_budgets(
    month: str | None = None,
    db: Session = Depends(get_db),
) -> list[BudgetEvalOut]:
    specs = _load_specs(db)
    if month:
        # When reviewing a specific month retrospectively, normalise any weekly/fortnightly
        # budget specs to their monthly target equivalent so Target vs. Actual is full-month.
        specs = [
            BudgetSpec(
                budget_id=s.budget_id,
                category_id=s.category_id,
                category_name=s.category_name,
                category_group=s.category_group,
                period="monthly",
                limit_cents=_to_monthly_cents(s.limit_cents, s.period),
                name=s.name,
            )
            for s in specs
        ]
    anchor = _resolve_month_anchor(db, month)
    txs = list(db.scalars(select(Transaction).options(joinedload(Transaction.category))).all())
    evals = evaluate_budgets(specs, _to_records(txs), anchor)
    return [BudgetEvalOut(**e.__dict__) for e in evals]


@router.post("", response_model=BudgetEvalOut, status_code=201)
def upsert_budget(payload: BudgetCreate, db: Session = Depends(get_db)) -> BudgetEvalOut:
    cat = db.get(Category, payload.category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="Category not found")
    if payload.limit_cents <= 0:
        raise HTTPException(status_code=400, detail="Budget limit must be positive")

    custom_name = payload.name.strip()
    existing = (
        db.scalar(
            select(Budget).where(
                Budget.category_id == payload.category_id,
                Budget.name == custom_name,
            )
        )
        if custom_name
        else None
    )
    if existing:
        existing.period = payload.period
        existing.limit_cents = payload.limit_cents
        existing.is_active = True
    else:
        existing = Budget(
            category_id=payload.category_id,
            name=custom_name,
            period=payload.period,
            limit_cents=payload.limit_cents,
            is_active=True,
        )
        db.add(existing)
    db.commit()

    txs = list(db.scalars(select(Transaction).options(joinedload(Transaction.category))).all())
    evals = evaluate_budgets(
        [
            BudgetSpec(
                budget_id=existing.id,
                category_id=cat.id,
                category_name=cat.name,
                category_group=cat.group,
                period=existing.period,
                limit_cents=existing.limit_cents,
                name=existing.name.strip() or cat.name,
            )
        ],
        _to_records(txs),
        _anchor_date(db),
    )
    return BudgetEvalOut(**evals[0].__dict__)


@router.patch("/{budget_id}", response_model=BudgetEvalOut)
def update_budget(
    budget_id: int,
    payload: BudgetUpdate,
    db: Session = Depends(get_db),
) -> BudgetEvalOut:
    b = db.scalar(
        select(Budget).options(joinedload(Budget.category)).where(Budget.id == budget_id)
    )
    if b is None:
        raise HTTPException(status_code=404, detail="Budget not found")
    if payload.name is not None:
        b.name = payload.name.strip()
    if payload.period is not None:
        b.period = payload.period
    if payload.limit_cents is not None:
        if payload.limit_cents <= 0:
            raise HTTPException(status_code=400, detail="Budget limit must be positive")
        b.limit_cents = payload.limit_cents
    db.commit()

    cat_name = b.category.name if b.category else "Unknown"
    cat_group = b.category.group if b.category else "Other"
    txs = list(db.scalars(select(Transaction).options(joinedload(Transaction.category))).all())
    evals = evaluate_budgets(
        [
            BudgetSpec(
                budget_id=b.id,
                category_id=b.category_id,
                category_name=cat_name,
                category_group=cat_group,
                period=b.period,
                limit_cents=b.limit_cents,
                name=b.name.strip() or cat_name,
            )
        ],
        _to_records(txs),
        _anchor_date(db),
    )
    return BudgetEvalOut(**evals[0].__dict__)


@router.delete("/{budget_id}", status_code=204)
def delete_budget(budget_id: int, db: Session = Depends(get_db)) -> None:
    b = db.get(Budget, budget_id)
    if b is None:
        raise HTTPException(status_code=404, detail="Budget not found")
    db.delete(b)
    db.commit()


@router.get("/recommendations", response_model=list[BudgetRecommendationOut])
def get_budget_recommendations(db: Session = Depends(get_db)) -> list[BudgetRecommendationOut]:
    txs = list(db.scalars(select(Transaction).options(joinedload(Transaction.category))).all())
    recs = recommend_budgets(_to_records(txs), _anchor_date(db), months=3)
    return [BudgetRecommendationOut(**r.__dict__) for r in recs]


@router.get("/pay-cycle", response_model=PayCyclePlanOut)
def get_pay_cycle_plan(
    basis: str = "salary",
    custom_fortnightly_cents: int | None = None,
    db: Session = Depends(get_db),
) -> PayCyclePlanOut:
    profile = db.scalar(select(IncomeProfile))
    gross_annual = from_cents(profile.gross_annual_cents) if profile else settings.gross_annual_salary
    pay_freq: PayFrequency = (profile.pay_frequency if profile else settings.pay_frequency)  # type: ignore[assignment]
    super_rate = Decimal(profile.super_rate_bps) / Decimal("10000") if profile else settings.super_rate
    tax_table = load_tax_table()

    est_period = net_per_period(gross_annual, pay_freq, tax_table, super_rate=super_rate)
    est_fn = net_per_period(gross_annual, "fortnightly", tax_table, super_rate=super_rate)
    est_mo = net_per_period(gross_annual, "monthly", tax_table, super_rate=super_rate)
    declared_fn_cents = to_cents(est_fn.net_period)
    declared_mo_cents = to_cents(est_mo.net_period)

    # Historical income, expenses, and per-category averages over recent 3 months (or all active months)
    anchor = _anchor_date(db)
    txs = list(db.scalars(select(Transaction).options(joinedload(Transaction.category))).all())
    records = _to_records(txs)

    cutoff_year = anchor.year
    cutoff_month = anchor.month - 2
    while cutoff_month <= 0:
        cutoff_month += 12
        cutoff_year -= 1
    window_start = date(cutoff_year, cutoff_month, 1)
    cur_month_start, cur_month_end = _month_bounds(anchor)

    active_months: set[tuple[int, int]] = set()
    hist_income_total = 0
    hist_expense_total = 0
    cat_window_totals: dict[tuple[int, str, str], int] = defaultdict(int)
    cat_current_month: dict[int, int] = defaultdict(int)

    for r in records:
        if r.kind != "actual" or r.is_transfer:
            continue
        if cur_month_start <= r.tx_date <= cur_month_end and r.amount_cents < 0 and r.category_id is not None:
            cat_current_month[r.category_id] += abs(r.amount_cents)
        if not (window_start <= r.tx_date <= anchor):
            continue
        active_months.add((r.tx_date.year, r.tx_date.month))
        if r.category_group == "Income" and r.amount_cents > 0:
            hist_income_total += r.amount_cents
        elif r.category_group != "Income" and r.amount_cents < 0:
            hist_expense_total += abs(r.amount_cents)
            if r.category_id is not None and r.category_name not in {"Uncategorised", "Internal transfer"}:
                cat_window_totals[(r.category_id, r.category_name, r.category_group)] += abs(r.amount_cents)

    divisor = max(1, len(active_months))
    hist_income_mo_cents = round(hist_income_total / divisor)
    hist_income_fn_cents = _to_period_cents(hist_income_mo_cents, "fortnightly")
    hist_expense_mo_cents = round(hist_expense_total / divisor)
    hist_expense_fn_cents = _to_period_cents(hist_expense_mo_cents, "fortnightly")

    category_averages: list[CategoryHistoricalSpendOut] = []
    seen_cats: set[int] = set()
    for (cid, cname, cgroup), total in sorted(cat_window_totals.items(), key=lambda x: x[1], reverse=True):
        seen_cats.add(cid)
        avg_mo = round(total / divisor)
        category_averages.append(
            CategoryHistoricalSpendOut(
                category_id=cid,
                category_name=cname,
                category_group=cgroup,
                avg_monthly_cents=avg_mo,
                avg_fortnightly_cents=_to_period_cents(avg_mo, "fortnightly"),
                current_month_cents=cat_current_month.get(cid, 0),
            )
        )

    # Determine active planning income basis
    normalized_basis = basis if basis in {"salary", "historical", "custom"} else "salary"
    if normalized_basis == "historical" and hist_income_mo_cents > 0:
        net_fn_cents = hist_income_fn_cents
        net_mo_cents = hist_income_mo_cents
        net_period_cents = _to_period_cents(hist_income_mo_cents, pay_freq)
    elif normalized_basis == "custom" and custom_fortnightly_cents is not None and custom_fortnightly_cents > 0:
        net_fn_cents = custom_fortnightly_cents
        net_mo_cents = _to_monthly_cents(custom_fortnightly_cents, "fortnightly")
        net_period_cents = _to_period_cents(net_mo_cents, pay_freq)
    elif profile and profile.custom_net_fortnightly_cents and profile.custom_net_fortnightly_cents > 0:
        normalized_basis = "custom"
        net_fn_cents = profile.custom_net_fortnightly_cents
        net_mo_cents = _to_monthly_cents(net_fn_cents, "fortnightly")
        net_period_cents = _to_period_cents(net_mo_cents, pay_freq)
    else:
        normalized_basis = "salary"
        net_fn_cents = declared_fn_cents
        net_mo_cents = declared_mo_cents
        net_period_cents = to_cents(est_period.net_period)

    goals = db.scalars(select(FinancialGoal)).all()
    fortnightly_goals = sum(
        contribution_to_fortnightly_cents(g.planned_contribution_cents, g.contribution_frequency)
        for g in goals
    )
    monthly_goals = _to_monthly_cents(fortnightly_goals, "fortnightly")
    if pay_freq == "weekly":
        goal_per_period = round(fortnightly_goals / 2)
    elif pay_freq == "monthly":
        goal_per_period = monthly_goals
    else:
        goal_per_period = fortnightly_goals

    rec_rows = db.scalars(
        select(RecurringPayment).where(RecurringPayment.cadence != "Dismissed")
    ).all()
    recurring_monthly_cents = sum(
        cadence_to_monthly_cents(r.amount_cents, r.cadence) for r in rec_rows
    )
    recurring_fortnightly_cents = _to_period_cents(recurring_monthly_cents, "fortnightly")
    recurring_per_period = _to_period_cents(recurring_monthly_cents, pay_freq)

    specs = _load_specs(db)
    budgeted_monthly_cents = sum(_to_monthly_cents(b.limit_cents, b.period) for b in specs)
    budgeted_fortnightly_cents = _to_period_cents(budgeted_monthly_cents, "fortnightly")

    plan = build_pay_cycle_plan(
        net_period_cents,
        pay_freq,
        specs,
        goal_per_period,
        recurring_bills_per_period_cents=recurring_per_period,
    )

    unallocated_fn_cents = (
        net_fn_cents
        - budgeted_fortnightly_cents
        - recurring_fortnightly_cents
        - fortnightly_goals
    )
    unallocated_mo_cents = (
        net_mo_cents
        - budgeted_monthly_cents
        - recurring_monthly_cents
        - monthly_goals
    )

    return PayCyclePlanOut(
        **plan.__dict__,
        income_basis=normalized_basis,
        declared_net_fortnightly_cents=declared_fn_cents,
        declared_net_monthly_cents=declared_mo_cents,
        historical_income_fortnightly_cents=hist_income_fn_cents,
        historical_income_monthly_cents=hist_income_mo_cents,
        historical_expenses_fortnightly_cents=hist_expense_fn_cents,
        historical_expenses_monthly_cents=hist_expense_mo_cents,
        net_fortnightly_cents=net_fn_cents,
        net_monthly_cents=net_mo_cents,
        budgeted_fortnightly_cents=budgeted_fortnightly_cents,
        budgeted_monthly_cents=budgeted_monthly_cents,
        recurring_bills_fortnightly_cents=recurring_fortnightly_cents,
        recurring_bills_monthly_cents=recurring_monthly_cents,
        goal_contributions_fortnightly_cents=fortnightly_goals,
        goal_contributions_monthly_cents=monthly_goals,
        unallocated_fortnightly_cents=unallocated_fn_cents,
        unallocated_monthly_cents=unallocated_mo_cents,
        category_averages=category_averages,
    )


@router.put("/net-pay", response_model=PayCyclePlanOut)
def update_net_pay(
    payload: NetPayUpdate,
    db: Session = Depends(get_db),
) -> PayCyclePlanOut:
    if payload.net_fortnightly_cents is not None and payload.net_fortnightly_cents <= 0:
        raise HTTPException(status_code=400, detail="Net pay must be positive")
    profile = db.scalar(select(IncomeProfile))
    if profile is None:
        profile = IncomeProfile(
            employer_name="Access4",
            gross_annual_cents=to_cents(settings.gross_annual_salary),
            pay_frequency=settings.pay_frequency,
            super_rate_bps=int(settings.super_rate * 10000),
            custom_net_fortnightly_cents=payload.net_fortnightly_cents,
        )
        db.add(profile)
    else:
        profile.custom_net_fortnightly_cents = payload.net_fortnightly_cents
    db.commit()
    return get_pay_cycle_plan(db=db)
