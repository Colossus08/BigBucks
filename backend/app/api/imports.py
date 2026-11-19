from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.importers.commbank_csv import compute_dedupe_hash, parse_commbank_csv
from app.models.finance import (
    Account,
    Category,
    ImportBatch,
    MerchantRule,
    RecurringPayment,
    Transaction,
)
from app.schemas.finance import ImportErrorOut, ImportReportOut
from app.services.categoriser import categorise_transaction, reconcile_rent_transactions
from app.services.savings import pair_internal_transfers

router = APIRouter(prefix="/api/imports", tags=["imports"])


@router.post("/commbank", response_model=ImportReportOut)
async def import_commbank_csv(
    account_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ImportReportOut:
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    raw_bytes = await file.read()
    try:
        content = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        content = raw_bytes.decode("latin-1")

    parsed = parse_commbank_csv(content)

    categories = list(db.scalars(select(Category)).all())
    categories_by_id = {c.id: c for c in categories}
    transfer_cat = next((c for c in categories if c.name == "Internal transfer"), None)
    uncat_cat = next((c for c in categories if c.name == "Uncategorised"), None)
    rules = list(db.scalars(select(MerchantRule).where(MerchantRule.is_active.is_(True))).all())

    existing_hashes = set(
        db.scalars(select(Transaction.dedupe_hash).where(Transaction.account_id == account_id)).all()
    )

    batch = ImportBatch(
        account_id=account_id,
        filename=file.filename or "upload.csv",
        total_rows=len(parsed.rows) + len(parsed.errors),
        error_rows=len(parsed.errors),
    )
    db.add(batch)
    db.flush()

    inserted = 0
    duplicates = 0
    seen_in_batch: set[str] = set()
    latest_date = None
    latest_balance_cents = None

    for row in parsed.rows:
        dedupe = compute_dedupe_hash(
            account_id=account_id,
            tx_date=row.tx_date,
            amount_cents=row.amount_cents,
            description_raw=row.description_raw,
            balance_cents=row.balance_cents,
        )
        if dedupe in existing_hashes or dedupe in seen_in_batch:
            duplicates += 1
            continue
        seen_in_batch.add(dedupe)

        cat_res = categorise_transaction(
            description_raw=row.description_raw,
            merchant=row.merchant,
            amount_cents=row.amount_cents,
            rules=rules,
            transfer_category_id=transfer_cat.id if transfer_cat else None,
            uncategorised_category_id=uncat_cat.id if uncat_cat else None,
            categories_by_id=categories_by_id,
        )

        db.add(
            Transaction(
                account_id=account_id,
                import_batch_id=batch.id,
                date=row.tx_date,
                amount_cents=row.amount_cents,
                description_raw=row.description_raw,
                merchant=row.merchant,
                balance_cents=row.balance_cents,
                category_id=cat_res.category_id,
                kind="actual",
                is_transfer=cat_res.is_transfer,
                dedupe_hash=dedupe,
                category_source=cat_res.category_source,
            )
        )
        inserted += 1

        if row.balance_cents is not None and (latest_date is None or row.tx_date >= latest_date):
            if latest_date is None or row.tx_date > latest_date:
                latest_date = row.tx_date
                latest_balance_cents = row.balance_cents

    # Refresh account balance from the newest transaction if present
    newest_tx = db.scalar(
        select(Transaction)
        .where(Transaction.account_id == account_id, Transaction.balance_cents.is_not(None))
        .order_by(Transaction.date.desc(), Transaction.id.asc())
        .limit(1)
    )
    if newest_tx and newest_tx.balance_cents is not None:
        account.current_balance_cents = newest_tx.balance_cents
    elif latest_balance_cents is not None:
        account.current_balance_cents = latest_balance_cents

    # Flush new rows first (autoflush=False), then pair cross-account internal transfers
    db.flush()
    pair_internal_transfers(db)
    reconcile_rent_transactions(db)
    rec_rows = db.scalars(select(RecurringPayment)).all()
    for r in rec_rows:
        needle = (r.merchant_pattern or r.merchant).strip().upper()
        if not needle:
            continue
        for row in parsed.rows:
            if row.amount_cents < 0 and (needle in row.merchant.upper() or needle in row.description_raw.upper()):
                r.last_charged_cents = abs(row.amount_cents)
                break

    batch.inserted_rows = inserted
    batch.duplicate_rows = duplicates
    db.commit()

    return ImportReportOut(
        batch_id=batch.id,
        filename=batch.filename,
        total_rows=batch.total_rows,
        inserted_rows=inserted,
        duplicate_rows=duplicates,
        error_rows=len(parsed.errors),
        errors=[
            ImportErrorOut(row_number=e.row_number, raw_line=e.raw_line, reason=e.reason)
            for e in parsed.errors
        ],
        balance_warnings=parsed.balance_warnings,
    )
