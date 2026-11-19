from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.finance import Budget, Category, MerchantRule, Transaction
from app.schemas.finance import CategoryCreate, CategoryOut

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)) -> list[Category]:
    return list(db.scalars(select(Category).order_by(Category.group, Category.name)).all())


@router.post("", response_model=CategoryOut, status_code=201)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)) -> Category:
    name = payload.name.strip()
    group = payload.group.strip() or "Lifestyle"
    if not name:
        raise HTTPException(status_code=400, detail="Category name cannot be empty")

    existing = db.scalar(
        select(Category).where(
            func.lower(Category.name) == name.lower(),
            func.lower(Category.group) == group.lower(),
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Category already exists in that group")

    cat = Category(
        name=name,
        group=group,
        is_income=payload.is_income or group == "Income",
        is_system=False,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db)) -> None:
    cat = db.get(Category, category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="Category not found")
    if cat.is_system:
        raise HTTPException(status_code=400, detail="System categories cannot be deleted")

    uncat = db.scalar(select(Category).where(Category.name == "Uncategorised"))
    fallback_id = uncat.id if uncat else None

    for tx in db.scalars(select(Transaction).where(Transaction.category_id == category_id)).all():
        tx.category_id = fallback_id
        tx.category_source = "default"

    for rule in db.scalars(select(MerchantRule).where(MerchantRule.category_id == category_id)).all():
        db.delete(rule)

    for b in db.scalars(select(Budget).where(Budget.category_id == category_id)).all():
        db.delete(b)

    db.delete(cat)
    db.commit()
