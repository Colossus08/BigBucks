from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.budgets import _anchor_date, _load_specs
from app.api.goals import goal_specs
from app.api.summary import _month_bounds, _to_records
from app.config import settings
from app.db import get_db
from app.engine.budgeting import evaluate_budgets
from app.engine.goals import contribution_to_fortnightly_cents, forecast_goal
from app.engine.income import net_per_period
from app.engine.insights import (
    RecurringItem,
    cadence_to_monthly_cents,
    compare_scenarios,
    detect_price_hikes,
    forecast_cashflow,
    generate_insights,
    suggest_recurring_candidates,
)
from app.engine.money import from_cents, to_cents
from app.engine.summary import summarise
from app.engine.tax import load_tax_table
from app.models.finance import (
    Account,
    Category,
    FinancialGoal,
    IncomeProfile,
    RecurringPayment,
    Transaction,
)
from app.schemas.finance import (
    ForecastPointOut,
    InsightOut,
    InsightsDashboardOut,
    PriceHikeAlertOut,
    RecurringCreate,
    RecurringDismiss,
    RecurringItemOut,
    RecurringSavedOut,
    ScenarioComparisonOut,
    ScenarioRequest,
)

from app.services.categoriser import reconcile_rent_transactions

router = APIRouter(prefix="/api/insights", tags=["insights"])


def _monthly_bases(db: Session, anchor: date) -> tuple[int, int, int, int]:
    accounts = db.scalars(select(Account).where(Account.is_own.is_(True))).all()
    starting_cash = sum(a.current_balance_cents for a in accounts if a.type == "transaction")

    tx_rows = list(db.scalars(select(Transaction).options(joinedload(Transaction.category))).all())
    records = _to_records(tx_rows)
    start, end = _month_bounds(anchor)
    month_sum = summarise(records, start_date=start, end_date=end)

    profile = db.scalar(select(IncomeProfile))
    gross_annual = from_cents(profile.gross_annual_cents) if profile else settings.gross_annual_salary
    super_rate = Decimal(profile.super_rate_bps) / Decimal("10000") if profile else settings.super_rate
    est_monthly = to_cents(net_per_period(gross_annual, "monthly", load_tax_table(), super_rate).net_period)

    monthly_income = month_sum.income_cents if month_sum.income_cents > 0 else est_monthly
    rec_rows = db.scalars(
        select(RecurringPayment).where(RecurringPayment.cadence != "Dismissed")
    ).all()
    recurring_monthly_cents = sum(
        cadence_to_monthly_cents(r.amount_cents, r.cadence) for r in rec_rows
    )
    monthly_expenses = max(month_sum.expenses_cents, recurring_monthly_cents)

    goals = db.scalars(select(FinancialGoal)).all()
    fortnightly_goals = sum(
        contribution_to_fortnightly_cents(g.planned_contribution_cents, g.contribution_frequency)
        for g in goals
    )
    monthly_goals = round(fortnightly_goals * 26 / 12)
    return starting_cash, monthly_income, monthly_expenses, monthly_goals


@router.get("", response_model=InsightsDashboardOut)
def get_insights(db: Session = Depends(get_db)) -> InsightsDashboardOut:
    anchor = _anchor_date(db)
    tx_rows = list(db.scalars(select(Transaction).options(joinedload(Transaction.category))).all())
    records = _to_records(tx_rows)
    start, end = _month_bounds(anchor)
    month_sum = summarise(records, start_date=start, end_date=end)

    budget_evals = evaluate_budgets(_load_specs(db), records, anchor)

    all_rec_rows = list(db.scalars(select(RecurringPayment).order_by(RecurringPayment.id.desc())).all())
    saved_rows = [r for r in all_rec_rows if r.cadence != "Dismissed"]
    saved_out = [
        RecurringSavedOut(
            id=r.id,
            merchant=r.merchant,
            category_name=r.category_name,
            amount_cents=r.amount_cents,
            cadence=r.cadence,
            estimated_monthly_cents=cadence_to_monthly_cents(r.amount_cents, r.cadence),
        )
        for r in saved_rows
    ]

    saved_as_items = [
        RecurringItem(
            merchant=r.merchant,
            category_name=r.category_name,
            occurrences=1,
            avg_amount_cents=r.amount_cents,
            estimated_cadence=r.cadence,
            estimated_monthly_cents=cadence_to_monthly_cents(r.amount_cents, r.cadence),
            last_date=anchor,
        )
        for r in saved_rows
    ]

    suggestions = suggest_recurring_candidates(
        (
            (
                tx.date,
                tx.amount_cents,
                tx.merchant,
                tx.category.name if tx.category else "Uncategorised",
                tx.is_transfer,
            )
            for tx in tx_rows
        ),
        already_saved_merchants={r.merchant for r in all_rec_rows},
    )

    goal_forecasts = [forecast_goal(spec, date.today()) for spec in goal_specs(db)]

    price_hikes = detect_price_hikes(
        ((r.id, r.merchant, r.merchant_pattern, r.amount_cents) for r in saved_rows),
        ((tx.date, tx.amount_cents, tx.merchant, tx.description_raw) for tx in tx_rows),
    )

    insights = generate_insights(month_sum, budget_evals, saved_as_items, goal_forecasts)
    starting_cash, m_income, m_expenses, m_goals = _monthly_bases(db, anchor)
    forecast = forecast_cashflow(starting_cash, m_income, m_expenses, m_goals)

    return InsightsDashboardOut(
        insights=[InsightOut(**i.__dict__) for i in insights],
        price_hike_alerts=[PriceHikeAlertOut(**a.__dict__) for a in price_hikes],
        recurring=saved_out,
        recurring_suggestions=[RecurringItemOut(**s.__dict__) for s in suggestions],
        forecast=[ForecastPointOut(**f.__dict__) for f in forecast],
        monthly_income_basis_cents=m_income,
        monthly_expense_basis_cents=m_expenses,
    )


@router.post("/recurring", response_model=RecurringSavedOut, status_code=201)
def add_recurring_payment(payload: RecurringCreate, db: Session = Depends(get_db)) -> RecurringSavedOut:
    merchant = payload.merchant.strip()
    if not merchant:
        raise HTTPException(status_code=400, detail="Merchant/name cannot be empty")
    if payload.amount_cents <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    cat_name = payload.category_name.strip() or "Other recurring payments"
    cat = db.scalar(select(Category).where(Category.name == cat_name))
    row = RecurringPayment(
        merchant=merchant,
        merchant_pattern=merchant.upper(),
        category_id=cat.id if cat else None,
        category_name=cat_name,
        amount_cents=payload.amount_cents,
        cadence=payload.cadence,
    )
    db.add(row)
    db.flush()
    reconcile_rent_transactions(db)
    db.commit()
    db.refresh(row)
    return RecurringSavedOut(
        id=row.id,
        merchant=row.merchant,
        category_name=row.category_name,
        amount_cents=row.amount_cents,
        cadence=row.cadence,
        estimated_monthly_cents=cadence_to_monthly_cents(row.amount_cents, row.cadence),
    )


@router.patch("/recurring/{recurring_id}", response_model=RecurringSavedOut)
def update_recurring_baseline(
    recurring_id: int,
    amount_cents: int,
    db: Session = Depends(get_db),
) -> RecurringSavedOut:
    row = db.get(RecurringPayment, recurring_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Recurring payment not found")
    if amount_cents <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    row.amount_cents = amount_cents
    row.last_charged_cents = amount_cents
    db.flush()
    reconcile_rent_transactions(db)
    db.commit()
    db.refresh(row)
    return RecurringSavedOut(
        id=row.id,
        merchant=row.merchant,
        category_name=row.category_name,
        amount_cents=row.amount_cents,
        cadence=row.cadence,
        estimated_monthly_cents=cadence_to_monthly_cents(row.amount_cents, row.cadence),
    )


@router.post("/recurring/dismiss", status_code=204)
def dismiss_recurring_suggestion(payload: RecurringDismiss, db: Session = Depends(get_db)) -> None:
    merchant = payload.merchant.strip()
    if not merchant:
        raise HTTPException(status_code=400, detail="Merchant cannot be empty")
    existing = db.scalar(
        select(RecurringPayment).where(
            RecurringPayment.merchant == merchant,
            RecurringPayment.cadence == "Dismissed",
        )
    )
    if existing is None:
        db.add(
            RecurringPayment(
                merchant=merchant,
                merchant_pattern=merchant.upper(),
                category_name=payload.category_name.strip() or "Other recurring payments",
                amount_cents=0,
                cadence="Dismissed",
            )
        )
        db.commit()


@router.delete("/recurring/{recurring_id}", status_code=204)
def delete_recurring_payment(recurring_id: int, db: Session = Depends(get_db)) -> None:
    row = db.get(RecurringPayment, recurring_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Recurring payment not found")
    db.delete(row)
    db.commit()


@router.post("/scenario", response_model=ScenarioComparisonOut)
def run_scenario(payload: ScenarioRequest, db: Session = Depends(get_db)) -> ScenarioComparisonOut:
    anchor = _anchor_date(db)
    starting_cash, m_income, m_expenses, m_goals = _monthly_bases(db, anchor)
    comp = compare_scenarios(
        starting_cash,
        m_income,
        m_expenses,
        m_goals,
        extra_monthly_savings_cents=payload.extra_monthly_savings_cents,
        monthly_income_delta_cents=payload.monthly_income_delta_cents,
    )
    return ScenarioComparisonOut(
        baseline=[ForecastPointOut(**f.__dict__) for f in comp.baseline],
        alternative=[ForecastPointOut(**f.__dict__) for f in comp.alternative],
        five_year_difference_cents=comp.five_year_difference_cents,
    )
