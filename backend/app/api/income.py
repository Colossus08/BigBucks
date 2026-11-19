from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.transactions import _to_out
from app.config import settings
from app.db import get_db
from app.engine.income import PayFrequency, net_per_period
from app.engine.money import from_cents, to_cents
from app.engine.tax import load_tax_table
from app.models.finance import Category, IncomeProfile, Transaction, WfhLog
from app.schemas.finance import (
    IncomeEstimateOut,
    IncomeProfileUpdate,
    SalaryReconciliationOut,
    TaxDeductionsDashboardOut,
    WfhLogCreate,
    WfhLogOut,
)

router = APIRouter(prefix="/api/income", tags=["income"])

# ATO fixed-rate method (cents per hour)
ATO_WFH_RATE_CENTS = 67


def _fy_bounds(fy: str | None) -> tuple[str, date, date]:
    today = date.today()
    if fy and "-" in fy:
        try:
            start_yr = int(fy.split("-")[0])
            return fy, date(start_yr, 7, 1), date(start_yr + 1, 6, 30)
        except ValueError:
            pass
    start_yr = today.year if today.month >= 7 else today.year - 1
    label = f"{start_yr}-{str(start_yr + 1)[-2:]}"
    return label, date(start_yr, 7, 1), date(start_yr + 1, 6, 30)


@router.get("/estimate", response_model=IncomeEstimateOut)
def get_income_estimate(
    freq: PayFrequency | None = Query(default=None),
    db: Session = Depends(get_db),
) -> IncomeEstimateOut:
    profile = db.scalar(select(IncomeProfile))
    employer_name = profile.employer_name if profile else "Access4"
    gross_annual = from_cents(profile.gross_annual_cents) if profile else settings.gross_annual_salary
    pay_freq: PayFrequency = freq or (profile.pay_frequency if profile else settings.pay_frequency)  # type: ignore[assignment]
    super_rate = (
        Decimal(profile.super_rate_bps) / Decimal("10000")
        if profile
        else settings.super_rate
    )

    rates = load_tax_table()
    est = net_per_period(gross_annual, pay_freq, rates, super_rate=super_rate)

    return IncomeEstimateOut(
        employer_name=employer_name,
        pay_frequency=est.pay_frequency,
        periods_per_year=est.periods_per_year,
        gross_annual=est.gross_annual,
        gross_period=est.gross_period,
        income_tax_period=est.income_tax_period,
        medicare_levy_period=est.medicare_levy_period,
        total_tax_period=est.total_tax_period,
        net_period=est.net_period,
        super_annual=est.super_annual,
        super_period=est.super_period,
        tax_year=rates.tax_year,
    )


@router.put("/profile", response_model=IncomeEstimateOut)
def update_income_profile(
    payload: IncomeProfileUpdate,
    db: Session = Depends(get_db),
) -> IncomeEstimateOut:
    if payload.gross_annual_cents <= 0:
        raise HTTPException(status_code=400, detail="Gross annual salary must be positive")
    profile = db.scalar(select(IncomeProfile))
    if profile is None:
        profile = IncomeProfile(
            employer_name=payload.employer_name.strip() or "Employer",
            gross_annual_cents=payload.gross_annual_cents,
            pay_frequency=payload.pay_frequency,
            super_rate_bps=payload.super_rate_bps,
        )
        db.add(profile)
    else:
        profile.employer_name = payload.employer_name.strip() or profile.employer_name
        profile.gross_annual_cents = payload.gross_annual_cents
        profile.pay_frequency = payload.pay_frequency
        profile.super_rate_bps = payload.super_rate_bps
    db.commit()
    return get_income_estimate(freq=None, db=db)


@router.get("/reconciliation", response_model=SalaryReconciliationOut)
def get_salary_reconciliation(db: Session = Depends(get_db)) -> SalaryReconciliationOut:
    """Match actual salary direct credits from bank statements against declared annualized income (§3.1)."""
    profile = db.scalar(select(IncomeProfile))
    employer_name = profile.employer_name if profile else "Access4"
    gross_annual = from_cents(profile.gross_annual_cents) if profile else settings.gross_annual_salary
    pay_freq: PayFrequency = (profile.pay_frequency if profile else settings.pay_frequency)  # type: ignore[assignment]
    super_rate = Decimal(profile.super_rate_bps) / Decimal("10000") if profile else settings.super_rate
    est = net_per_period(gross_annual, pay_freq, load_tax_table(), super_rate=super_rate)
    expected_net_cents = to_cents(est.net_period)

    salary_cat_id = db.scalar(select(Category.id).where(Category.name == "Salary"))
    deposits: list[Transaction] = []
    if salary_cat_id is not None:
        deposits = list(
            db.scalars(
                select(Transaction).where(
                    Transaction.category_id == salary_cat_id,
                    Transaction.amount_cents > 0,
                    Transaction.kind == "actual",
                )
            ).all()
        )

    count = len(deposits)
    ytd_cents = sum(d.amount_cents for d in deposits)
    avg_cents = round(ytd_cents / count) if count > 0 else 0
    variance = (avg_cents - expected_net_cents) if count > 0 else 0

    return SalaryReconciliationOut(
        employer_name=employer_name,
        pay_frequency=pay_freq,
        expected_net_period_cents=expected_net_cents,
        actual_avg_period_cents=avg_cents,
        ytd_actual_salary_cents=ytd_cents,
        salary_deposit_count=count,
        variance_cents=variance,
    )


@router.get("/tax-deductions", response_model=TaxDeductionsDashboardOut)
def get_tax_deductions(
    fy: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> TaxDeductionsDashboardOut:
    label, start, end = _fy_bounds(fy)
    wfh_rows = list(
        db.scalars(
            select(WfhLog)
            .where(WfhLog.work_date >= start, WfhLog.work_date <= end)
            .order_by(WfhLog.work_date.desc())
        ).all()
    )
    deductible_txs = list(
        db.scalars(
            select(Transaction)
            .options(joinedload(Transaction.category))
            .where(
                Transaction.is_tax_deductible.is_(True),
                Transaction.date >= start,
                Transaction.date <= end,
            )
            .order_by(Transaction.date.desc())
        ).all()
    )

    total_hours = round(sum(w.hours for w in wfh_rows), 2)
    wfh_cents = round(total_hours * ATO_WFH_RATE_CENTS)
    expense_cents = sum(abs(t.amount_cents) for t in deductible_txs if t.amount_cents < 0)

    return TaxDeductionsDashboardOut(
        financial_year=label,
        wfh_hours_total=total_hours,
        wfh_deduction_cents=wfh_cents,
        expense_deduction_cents=expense_cents,
        total_claimable_cents=wfh_cents + expense_cents,
        wfh_logs=[WfhLogOut.model_validate(w) for w in wfh_rows],
        deductible_transactions=[_to_out(t) for t in deductible_txs],
    )


@router.post("/wfh", response_model=WfhLogOut, status_code=201)
def add_wfh_log(payload: WfhLogCreate, db: Session = Depends(get_db)) -> WfhLogOut:
    if payload.hours <= 0 or payload.hours > 24:
        raise HTTPException(status_code=400, detail="Hours must be between 0 and 24")
    row = WfhLog(work_date=payload.work_date, hours=payload.hours, note=payload.note.strip())
    db.add(row)
    db.commit()
    db.refresh(row)
    return WfhLogOut.model_validate(row)


@router.delete("/wfh/{log_id}", status_code=204)
def delete_wfh_log(log_id: int, db: Session = Depends(get_db)) -> None:
    row = db.get(WfhLog, log_id)
    if row is None:
        raise HTTPException(status_code=404, detail="WFH log not found")
    db.delete(row)
    db.commit()
