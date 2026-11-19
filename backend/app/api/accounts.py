from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.engine.savings import MASK_RE, parse_transfer_mask, suggest_transfer_counterparties
from app.models.finance import Account, FinancialGoal, Institution, Transaction
from app.schemas.finance import (
    AccountCreate,
    AccountOut,
    SavingsAccountOut,
    TransferSuggestionOut,
)
from app.services.savings import net_moved_by_account_id, tracked_savings_accounts, transfer_rows

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountOut])
def list_accounts(db: Session = Depends(get_db)) -> list[Account]:
    return list(db.scalars(select(Account).order_by(Account.id)).all())


@router.get("/savings", response_model=list[SavingsAccountOut])
def list_savings_accounts(db: Session = Depends(get_db)) -> list[SavingsAccountOut]:
    accounts = tracked_savings_accounts(db)
    moved = net_moved_by_account_id(db)
    counts: dict[str, int] = {}
    for _, _, desc in transfer_rows(db):
        mask = parse_transfer_mask(desc)
        if mask:
            counts[mask] = counts.get(mask, 0) + 1
    return [
        SavingsAccountOut(
            id=a.id,
            name=a.name,
            net_moved_cents=moved.get(a.id, 0),
            transfer_count=counts.get(a.account_number_mask.lower(), 0),
        )
        for a in accounts
    ]


@router.get("/transfer-suggestions", response_model=list[TransferSuggestionOut])
def list_transfer_suggestions(db: Session = Depends(get_db)) -> list[TransferSuggestionOut]:
    tracked = {a.account_number_mask for a in tracked_savings_accounts(db)}
    found = suggest_transfer_counterparties(transfer_rows(db), tracked)
    return [
        TransferSuggestionOut(mask=f.mask, count=f.count, net_moved_cents=f.net_moved_in_cents)
        for f in found
    ]


@router.post("", response_model=AccountOut, status_code=201)
def create_account(payload: AccountCreate, db: Session = Depends(get_db)) -> Account:
    commbank = db.scalar(select(Institution).where(Institution.code == "commbank"))
    if commbank is None:
        raise HTTPException(status_code=400, detail="Default institution not seeded")

    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Account name cannot be empty")

    mask = payload.account_number_mask.strip().lower()
    if payload.type == "savings":
        if not MASK_RE.match(mask):
            raise HTTPException(status_code=400, detail="Savings accounts need a mask like xx0464")
        existing = db.scalar(
            select(Account).where(Account.type == "savings", func.lower(Account.account_number_mask) == mask)
        )
        if existing is not None:
            raise HTTPException(status_code=409, detail="That account is already being tracked")

    account = Account(
        institution_id=commbank.id,
        name=name,
        account_number_mask=mask,
        type=payload.type,
        is_own=payload.is_own,
        current_balance_cents=0,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=204)
def delete_account(account_id: int, db: Session = Depends(get_db)) -> None:
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    tx_count = db.scalar(select(func.count()).select_from(Transaction).where(Transaction.account_id == account_id))
    if tx_count:
        raise HTTPException(status_code=400, detail="Cannot remove an account that has imported transactions")

    for goal in db.scalars(select(FinancialGoal).where(FinancialGoal.linked_account_id == account_id)).all():
        goal.linked_account_id = None
    db.delete(account)
    db.commit()
