from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.engine.money import from_cents, to_cents
from app.engine.wealth import HoldingSpec, evaluate_portfolio, project_superannuation
from app.models.finance import Account, IncomeProfile, InvestmentHolding, SuperAccount
from app.schemas.finance import (
    HoldingCreate,
    HoldingOut,
    HoldingPriceUpdate,
    SuperProjectionOut,
    SuperUpdate,
    WealthDashboardOut,
)

router = APIRouter(prefix="/api/wealth", tags=["wealth"])


@router.get("", response_model=WealthDashboardOut)
def get_wealth_dashboard(db: Session = Depends(get_db)) -> WealthDashboardOut:
    accounts = db.scalars(select(Account).where(Account.is_own.is_(True))).all()
    cash_cents = sum(a.current_balance_cents for a in accounts)

    holdings_rows = db.scalars(select(InvestmentHolding).order_by(InvestmentHolding.symbol)).all()
    portfolio = evaluate_portfolio(
        HoldingSpec(
            holding_id=h.id,
            symbol=h.symbol,
            name=h.name,
            asset_type=h.asset_type,
            units_milli=h.units_milli,
            avg_cost_cents=h.avg_cost_cents,
            current_price_cents=h.current_price_cents,
        )
        for h in holdings_rows
    )

    super_acc = db.scalar(select(SuperAccount))
    if super_acc is None:
        super_acc = SuperAccount(fund_name="MySuper Account", balance_cents=0, personal_monthly_cents=0, expected_return_bps=700)
        db.add(super_acc)
        db.commit()
        db.refresh(super_acc)

    profile = db.scalar(select(IncomeProfile))
    gross_annual = from_cents(profile.gross_annual_cents) if profile else settings.gross_annual_salary
    super_rate = Decimal(profile.super_rate_bps) / Decimal("10000") if profile else settings.super_rate
    annual_employer_cents = to_cents(gross_annual * super_rate)

    projections = project_superannuation(
        starting_balance_cents=super_acc.balance_cents,
        annual_employer_cents=annual_employer_cents,
        personal_monthly_cents=super_acc.personal_monthly_cents,
        expected_return_bps=super_acc.expected_return_bps,
    )

    net_worth_cents = cash_cents + portfolio.total_value_cents + super_acc.balance_cents

    return WealthDashboardOut(
        cash_cents=cash_cents,
        investments_value_cents=portfolio.total_value_cents,
        investments_cost_cents=portfolio.total_cost_cents,
        investments_gain_loss_cents=portfolio.total_gain_loss_cents,
        super_fund_name=super_acc.fund_name,
        super_balance_cents=super_acc.balance_cents,
        super_personal_monthly_cents=super_acc.personal_monthly_cents,
        super_expected_return_bps=super_acc.expected_return_bps,
        net_worth_cents=net_worth_cents,
        holdings=[HoldingOut(**h.__dict__) for h in portfolio.holdings],
        super_projections=[SuperProjectionOut(**p.__dict__) for p in projections],
    )


@router.post("/holdings", response_model=HoldingOut, status_code=201)
def add_holding(payload: HoldingCreate, db: Session = Depends(get_db)) -> HoldingOut:
    h = InvestmentHolding(
        symbol=payload.symbol.strip().upper(),
        name=payload.name.strip(),
        asset_type=payload.asset_type,
        units_milli=int((payload.units * Decimal("1000")).quantize(Decimal("1"))),
        avg_cost_cents=payload.avg_cost_cents,
        current_price_cents=payload.current_price_cents,
    )
    db.add(h)
    db.commit()
    db.refresh(h)
    portfolio = evaluate_portfolio(
        [
            HoldingSpec(
                holding_id=h.id,
                symbol=h.symbol,
                name=h.name,
                asset_type=h.asset_type,
                units_milli=h.units_milli,
                avg_cost_cents=h.avg_cost_cents,
                current_price_cents=h.current_price_cents,
            )
        ]
    )
    return HoldingOut(**portfolio.holdings[0].__dict__)


@router.patch("/holdings/{holding_id}", response_model=HoldingOut)
def refresh_holding_valuation(
    holding_id: int,
    payload: HoldingPriceUpdate,
    db: Session = Depends(get_db),
) -> HoldingOut:
    h = db.get(InvestmentHolding, holding_id)
    if h is None:
        raise HTTPException(status_code=404, detail="Holding not found")
    if payload.current_price_cents <= 0:
        raise HTTPException(status_code=400, detail="Price must be positive")
    h.current_price_cents = payload.current_price_cents
    if payload.units is not None and payload.units > 0:
        h.units_milli = int((payload.units * Decimal("1000")).quantize(Decimal("1")))
    db.commit()
    db.refresh(h)
    portfolio = evaluate_portfolio(
        [
            HoldingSpec(
                holding_id=h.id,
                symbol=h.symbol,
                name=h.name,
                asset_type=h.asset_type,
                units_milli=h.units_milli,
                avg_cost_cents=h.avg_cost_cents,
                current_price_cents=h.current_price_cents,
            )
        ]
    )
    return HoldingOut(**portfolio.holdings[0].__dict__)


@router.delete("/holdings/{holding_id}", status_code=204)
def delete_holding(holding_id: int, db: Session = Depends(get_db)) -> None:
    h = db.get(InvestmentHolding, holding_id)
    if h is None:
        raise HTTPException(status_code=404, detail="Holding not found")
    db.delete(h)
    db.commit()


@router.put("/super", response_model=WealthDashboardOut)
def update_super(payload: SuperUpdate, db: Session = Depends(get_db)) -> WealthDashboardOut:
    super_acc = db.scalar(select(SuperAccount))
    if super_acc is None:
        super_acc = SuperAccount()
        db.add(super_acc)
    super_acc.fund_name = payload.fund_name.strip()
    super_acc.balance_cents = max(0, payload.balance_cents)
    super_acc.personal_monthly_cents = max(0, payload.personal_monthly_cents)
    super_acc.expected_return_bps = payload.expected_return_bps
    db.commit()
    return get_wealth_dashboard(db)
