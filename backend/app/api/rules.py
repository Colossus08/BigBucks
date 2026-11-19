from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.finance import Category, MerchantRule, Transaction
from app.schemas.finance import RuleApplyResult, RuleCreate, RuleOut
from app.services.categoriser import (
    _matches_rule,
    categorise_transaction,
    reconcile_rent_transactions,
)

router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("", response_model=list[RuleOut])
def list_rules(db: Session = Depends(get_db)) -> list[RuleOut]:
    cats = {c.id: c.name for c in db.scalars(select(Category)).all()}
    rules = db.scalars(
        select(MerchantRule)
        .where(MerchantRule.is_active.is_(True))
        .order_by(MerchantRule.source.asc(), MerchantRule.id.desc())
    ).all()
    return [
        RuleOut(
            id=r.id,
            pattern=r.pattern,
            match_type=r.match_type,
            category_id=r.category_id,
            category_name=cats.get(r.category_id, ""),
            priority=r.priority,
            source=r.source,
            is_active=r.is_active,
        )
        for r in rules
    ]


def _reapply_rules_to_uncategorised(db: Session) -> int:
    categories = list(db.scalars(select(Category)).all())
    categories_by_id = {c.id: c for c in categories}
    transfer_cat = next((c for c in categories if c.name == "Internal transfer"), None)
    uncat_cat = next((c for c in categories if c.name == "Uncategorised"), None)
    rules = list(db.scalars(select(MerchantRule).where(MerchantRule.is_active.is_(True))).all())

    if uncat_cat is None:
        return 0

    uncat_txs = db.scalars(
        select(Transaction).where(
            (Transaction.category_id == uncat_cat.id) | (Transaction.category_id.is_(None))
        )
    ).all()

    updated = 0
    for tx in uncat_txs:
        res = categorise_transaction(
            description_raw=tx.description_raw,
            merchant=tx.merchant,
            amount_cents=tx.amount_cents,
            rules=rules,
            transfer_category_id=transfer_cat.id if transfer_cat else None,
            uncategorised_category_id=uncat_cat.id,
            categories_by_id=categories_by_id,
        )
        if res.category_id != uncat_cat.id:
            tx.category_id = res.category_id
            tx.is_transfer = res.is_transfer
            tx.category_source = res.category_source
            updated += 1

    reconcile_rent_transactions(db)
    db.commit()
    return updated


def _undo_rule(db: Session, rule: MerchantRule) -> int:
    uncat_cat = db.scalar(select(Category).where(Category.name == "Uncategorised"))
    uncat_id = uncat_cat.id if uncat_cat else None

    matching_txs = db.scalars(
        select(Transaction).where(Transaction.category_id == rule.category_id)
    ).all()

    reset_count = 0
    for tx in matching_txs:
        if _matches_rule(rule, tx.merchant, tx.description_raw):
            tx.category_id = uncat_id
            tx.is_transfer = False
            tx.category_source = "default"
            reset_count += 1

    db.delete(rule)
    db.flush()
    # Re-apply remaining rules (so e.g. internal transfer detection or seed rules take over)
    _reapply_rules_to_uncategorised(db)
    return reset_count


@router.post("", response_model=RuleApplyResult, status_code=201)
def create_rule(payload: RuleCreate, db: Session = Depends(get_db)) -> RuleApplyResult:
    pattern = payload.pattern.strip()
    if not pattern:
        raise HTTPException(status_code=400, detail="Pattern cannot be empty")
    cat = db.get(Category, payload.category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="Category not found")

    db.add(
        MerchantRule(
            pattern=pattern,
            match_type=payload.match_type,
            category_id=payload.category_id,
            priority=20,
            source="learned",
            is_active=True,
        )
    )
    db.flush()
    updated = _reapply_rules_to_uncategorised(db)
    return RuleApplyResult(updated_count=updated)


@router.post("/reapply", response_model=RuleApplyResult)
def reapply_rules(db: Session = Depends(get_db)) -> RuleApplyResult:
    updated = _reapply_rules_to_uncategorised(db)
    return RuleApplyResult(updated_count=updated)


@router.post("/undo-latest", response_model=RuleApplyResult)
def undo_latest_rule(db: Session = Depends(get_db)) -> RuleApplyResult:
    latest = db.scalar(
        select(MerchantRule)
        .where(MerchantRule.source == "learned", MerchantRule.is_active.is_(True))
        .order_by(MerchantRule.id.desc())
        .limit(1)
    )
    if latest is None:
        raise HTTPException(status_code=404, detail="No learned rules to undo")
    reset_count = _undo_rule(db, latest)
    return RuleApplyResult(updated_count=reset_count)


@router.patch("/{rule_id}", response_model=RuleApplyResult)
def update_rule_category(
    rule_id: int,
    category_id: int,
    db: Session = Depends(get_db),
) -> RuleApplyResult:
    rule = db.get(MerchantRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    cat = db.get(Category, category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="Category not found")

    rule.category_id = category_id
    is_transfer = cat.group == "Transfer"

    txs = db.scalars(select(Transaction)).all()
    updated = 0
    for tx in txs:
        if _matches_rule(rule, tx.merchant, tx.description_raw):
            tx.category_id = category_id
            tx.is_transfer = is_transfer
            tx.category_source = "user" if rule.source == "learned" else "rule"
            updated += 1

    db.commit()
    return RuleApplyResult(updated_count=updated)


@router.delete("/{rule_id}", response_model=RuleApplyResult)
def delete_rule(rule_id: int, db: Session = Depends(get_db)) -> RuleApplyResult:
    rule = db.get(MerchantRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    reset_count = _undo_rule(db, rule)
    return RuleApplyResult(updated_count=reset_count)
