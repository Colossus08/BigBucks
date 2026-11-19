from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.savings import net_moved_by_mask
from app.models.finance import Account, Category, Transaction


def tracked_savings_accounts(db: Session) -> list[Account]:
    return list(db.scalars(select(Account).where(Account.type == "savings").order_by(Account.id)).all())


def transfer_rows(db: Session) -> list[tuple[date, int, str]]:
    """(date, amount, description) of transactions on your spending accounts that look like transfers."""
    stmt = (
        select(Transaction.date, Transaction.amount_cents, Transaction.description_raw)
        .join(Account, Account.id == Transaction.account_id)
        .where(Account.type == "transaction", Transaction.description_raw.ilike("Transfer %"))
    )
    return [(d, a, desc) for d, a, desc in db.execute(stmt).all()]


def net_moved_by_account_id(
    db: Session,
    start: date | None = None,
    end: date | None = None,
) -> dict[int, int]:
    """Net money moved into each tracked savings account (from mask transfers + paired credits)."""
    accounts = tracked_savings_accounts(db)
    if not accounts:
        return {}
    by_mask = net_moved_by_mask(transfer_rows(db), start, end)
    result: dict[int, int] = {}
    for a in accounts:
        mask_total = by_mask.get(a.account_number_mask.lower(), 0)
        # Also include direct/paired transactions recorded on the savings account itself if any exist
        stmt = select(Transaction).where(
            Transaction.account_id == a.id,
            Transaction.paired_transaction_id.is_not(None),
        )
        if start:
            stmt = stmt.where(Transaction.date >= start)
        if end:
            stmt = stmt.where(Transaction.date <= end)
        direct_rows = db.scalars(stmt).all()
        direct_total = sum(tx.amount_cents for tx in direct_rows)
        # Avoid double-counting when the spending-side transfer already matched by mask
        result[a.id] = mask_total if mask_total != 0 else direct_total
    return result


def pair_internal_transfers(db: Session) -> int:
    """Pair matching opposite-sign transactions across owned accounts within a 0-48h window (§4.3)."""
    own_account_ids = set(
        db.scalars(select(Account.id).where(Account.is_own.is_(True))).all()
    )
    if len(own_account_ids) < 2:
        return 0

    transfer_cat = db.scalar(select(Category).where(Category.name == "Internal transfer"))
    transfer_cat_id = transfer_cat.id if transfer_cat else None

    unpaired = list(
        db.scalars(
            select(Transaction)
            .where(
                Transaction.account_id.in_(own_account_ids),
                Transaction.paired_transaction_id.is_(None),
                Transaction.amount_cents != 0,
            )
            .order_by(Transaction.date.asc(), Transaction.id.asc())
        ).all()
    )

    debits = [t for t in unpaired if t.amount_cents < 0]
    credits = [t for t in unpaired if t.amount_cents > 0]
    used_credit_ids: set[int] = set()
    paired_count = 0

    for d in debits:
        for c in credits:
            if c.id in used_credit_ids or c.account_id == d.account_id:
                continue
            if abs(d.amount_cents) != abs(c.amount_cents):
                continue
            if abs((d.date - c.date).days) <= 2:
                d.paired_transaction_id = c.id
                c.paired_transaction_id = d.id
                d.is_transfer = True
                c.is_transfer = True
                if transfer_cat_id is not None:
                    d.category_id = transfer_cat_id
                    c.category_id = transfer_cat_id
                used_credit_ids.add(c.id)
                paired_count += 1
                break

    db.flush()
    return paired_count
