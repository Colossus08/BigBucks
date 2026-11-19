from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models.finance import Category, Transaction
from app.schemas.finance import (
    BulkCategoriseRequest,
    RuleApplyResult,
    TransactionOut,
    TransactionSplitOut,
    TransactionSplitRequest,
    TransactionUpdate,
    TransactionUpdateOut,
    UncategorisedMerchantOut,
)
from app.services.categoriser import (
    apply_learned_merchant_rule,
    split_transaction,
    unsplit_transaction,
)

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def _to_out(tx: Transaction) -> TransactionOut:
    cat_name = tx.category.name if tx.category else "Uncategorised"
    cat_group = tx.category.group if tx.category else "Other"
    return TransactionOut(
        id=tx.id,
        account_id=tx.account_id,
        date=tx.date,
        amount_cents=tx.amount_cents,
        description_raw=tx.description_raw,
        merchant=tx.merchant,
        balance_cents=tx.balance_cents,
        category_id=tx.category_id,
        category_name=cat_name,
        category_group=cat_group,
        kind=tx.kind,
        is_transfer=tx.is_transfer,
        paired_transaction_id=tx.paired_transaction_id,
        is_tax_deductible=tx.is_tax_deductible,
        deduction_category=tx.deduction_category,
        receipt_ref=tx.receipt_ref,
        category_source=tx.category_source,
    )


@router.get("/count")
def count_transactions(db: Session = Depends(get_db)) -> dict[str, int]:
    return {"count": db.scalar(select(func.count()).select_from(Transaction)) or 0}


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    category: int | None = None,
    account: int | None = None,
    q: str | None = None,
    min_cents: int | None = Query(default=None, alias="min"),
    max_cents: int | None = Query(default=None, alias="max"),
    limit: int = Query(default=5000, ge=1, le=20000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[TransactionOut]:
    stmt = select(Transaction).options(joinedload(Transaction.category))

    if from_date:
        stmt = stmt.where(Transaction.date >= from_date)
    if to_date:
        stmt = stmt.where(Transaction.date <= to_date)
    if category is not None:
        stmt = stmt.where(Transaction.category_id == category)
    if account is not None:
        stmt = stmt.where(Transaction.account_id == account)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Transaction.merchant.ilike(like), Transaction.description_raw.ilike(like)))
    if min_cents is not None:
        stmt = stmt.where(Transaction.amount_cents >= min_cents)
    if max_cents is not None:
        stmt = stmt.where(Transaction.amount_cents <= max_cents)

    stmt = stmt.order_by(Transaction.date.desc(), Transaction.id.asc()).offset(offset).limit(limit)
    rows = db.scalars(stmt).all()
    return [_to_out(tx) for tx in rows]


@router.patch("/{transaction_id}", response_model=TransactionUpdateOut)
def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    db: Session = Depends(get_db),
) -> TransactionUpdateOut:
    tx = db.scalar(
        select(Transaction)
        .options(joinedload(Transaction.category))
        .where(Transaction.id == transaction_id)
    )
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    updated_count = 0
    if payload.excluded is not None:
        tx.kind = "excluded" if payload.excluded else "actual"
        updated_count = 1
    if payload.is_tax_deductible is not None:
        tx.is_tax_deductible = payload.is_tax_deductible
        updated_count = 1
    if payload.deduction_category is not None:
        tx.deduction_category = payload.deduction_category or None
        updated_count = 1
    if payload.receipt_ref is not None:
        tx.receipt_ref = payload.receipt_ref.strip() or None
        updated_count = 1

    if payload.category_id is not None:
        cat = db.get(Category, payload.category_id)
        if cat is None:
            raise HTTPException(status_code=404, detail="Category not found")

        if payload.apply_to_merchant:
            updated_count = apply_learned_merchant_rule(db, tx.merchant, cat.id)
        else:
            tx.category_id = cat.id
            tx.is_transfer = cat.group == "Transfer"
            tx.category_source = "manual"
            updated_count = max(1, updated_count)

    db.commit()
    db.refresh(tx)
    return TransactionUpdateOut(transaction=_to_out(tx), updated_count=updated_count)


@router.post("/{transaction_id}/split", response_model=TransactionSplitOut)
def split_transaction_endpoint(
    transaction_id: int,
    payload: TransactionSplitRequest,
    db: Session = Depends(get_db),
) -> TransactionSplitOut:
    tx = db.scalar(
        select(Transaction)
        .options(joinedload(Transaction.category))
        .where(Transaction.id == transaction_id)
    )
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    try:
        child = split_transaction(
            db=db,
            tx=tx,
            split_amount_cents=payload.split_amount_cents,
            split_category_id=payload.category_id,
            note=payload.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.commit()
    db.refresh(tx)
    child_loaded = db.scalar(
        select(Transaction)
        .options(joinedload(Transaction.category))
        .where(Transaction.id == child.id)
    )
    return TransactionSplitOut(parent=_to_out(tx), child=_to_out(child_loaded or child))


@router.post("/{transaction_id}/unsplit", response_model=TransactionOut)
def unsplit_transaction_endpoint(
    transaction_id: int,
    db: Session = Depends(get_db),
) -> TransactionOut:
    child_tx = db.scalar(
        select(Transaction)
        .options(joinedload(Transaction.category))
        .where(Transaction.id == transaction_id)
    )
    if child_tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    try:
        parent = unsplit_transaction(db=db, child_tx=child_tx)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.commit()
    parent_loaded = db.scalar(
        select(Transaction)
        .options(joinedload(Transaction.category))
        .where(Transaction.id == parent.id)
    )
    return _to_out(parent_loaded or parent)


@router.get("/merchants/uncategorised", response_model=list[UncategorisedMerchantOut])
def list_uncategorised_merchants(db: Session = Depends(get_db)) -> list[UncategorisedMerchantOut]:
    uncat = db.scalar(select(Category).where(Category.name == "Uncategorised"))
    stmt = select(Transaction)
    if uncat is not None:
        stmt = stmt.where((Transaction.category_id == uncat.id) | (Transaction.category_id.is_(None)))
    else:
        stmt = stmt.where(Transaction.category_id.is_(None))

    txs = db.scalars(stmt.order_by(Transaction.date.desc())).all()
    grouped: dict[str, dict] = {}
    for tx in txs:
        entry = grouped.get(tx.merchant)
        if entry is None:
            grouped[tx.merchant] = {
                "merchant": tx.merchant,
                "count": 1,
                "total_cents": tx.amount_cents,
                "sample_description": tx.description_raw,
                "sample_transaction_id": tx.id,
            }
        else:
            entry["count"] += 1
            entry["total_cents"] += tx.amount_cents

    ordered = sorted(grouped.values(), key=lambda x: (x["count"], abs(x["total_cents"])), reverse=True)
    return [UncategorisedMerchantOut(**item) for item in ordered]


@router.post("/bulk-categorise", response_model=RuleApplyResult)
def bulk_categorise_merchants(
    payload: BulkCategoriseRequest,
    db: Session = Depends(get_db),
) -> RuleApplyResult:
    if not payload.merchants:
        return RuleApplyResult(updated_count=0)
    cat = db.get(Category, payload.category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="Category not found")

    total_updated = 0
    for merchant in payload.merchants:
        total_updated += apply_learned_merchant_rule(db, merchant, cat.id)
    db.commit()
    return RuleApplyResult(updated_count=total_updated)
