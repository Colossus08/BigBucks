import csv
import io
import sqlite3
import tempfile
from pathlib import Path
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.income import ATO_WFH_RATE_CENTS, _fy_bounds
from app.db import get_db
from app.engine.money import from_cents
from app.models.finance import Transaction, WfhLog

router = APIRouter(prefix="/api/exports", tags=["exports"])


@router.get("/transactions.csv")
def export_transactions_csv(db: Session = Depends(get_db)) -> Response:
    rows = db.scalars(
        select(Transaction)
        .options(joinedload(Transaction.category))
        .order_by(Transaction.date.desc(), Transaction.id.asc())
    ).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "id",
            "date",
            "merchant",
            "description_raw",
            "category_group",
            "category_name",
            "amount_aud",
            "balance_aud",
            "is_transfer",
            "kind",
        ]
    )
    for tx in rows:
        writer.writerow(
            [
                tx.id,
                tx.date.isoformat(),
                tx.merchant,
                tx.description_raw,
                tx.category.group if tx.category else "Other",
                tx.category.name if tx.category else "Uncategorised",
                f"{from_cents(tx.amount_cents):.2f}",
                f"{from_cents(tx.balance_cents):.2f}" if tx.balance_cents is not None else "",
                "true" if tx.is_transfer else "false",
                tx.kind,
            ]
        )

    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="transactions_export.csv"'},
    )


@router.get("/backup.db")
def export_sqlite_backup(db: Session = Depends(get_db)) -> Response:
    raw_conn = db.connection().connection.driver_connection
    with tempfile.TemporaryDirectory() as tmp_dir:
        backup_path = Path(tmp_dir) / "finance_backup.db"
        dest = sqlite3.connect(backup_path)
        try:
            raw_conn.backup(dest)
        finally:
            dest.close()
        data = backup_path.read_bytes()

    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": 'attachment; filename="finance_backup.db"'},
    )


@router.get("/tax-deductions.csv")
def export_tax_deductions_csv(
    fy: str | None = None,
    db: Session = Depends(get_db),
) -> Response:
    label, start, end = _fy_bounds(fy)
    wfh_rows = list(
        db.scalars(
            select(WfhLog)
            .where(WfhLog.work_date >= start, WfhLog.work_date <= end)
            .order_by(WfhLog.work_date.asc())
        ).all()
    )
    tx_rows = list(
        db.scalars(
            select(Transaction)
            .options(joinedload(Transaction.category))
            .where(
                Transaction.is_tax_deductible.is_(True),
                Transaction.date >= start,
                Transaction.date <= end,
            )
            .order_by(Transaction.date.asc())
        ).all()
    )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ATO Financial Year", label, "Period", f"{start.isoformat()} to {end.isoformat()}"])
    writer.writerow([])
    writer.writerow(["Section", "Date", "Claim Code / Type", "Merchant / Note", "Receipt Ref", "Hours", "Claimable AUD"])

    for tx in tx_rows:
        writer.writerow(
            [
                "Expense Deduction",
                tx.date.isoformat(),
                tx.deduction_category or "D5",
                tx.merchant,
                tx.receipt_ref or "",
                "",
                f"{from_cents(abs(tx.amount_cents)):.2f}",
            ]
        )

    for w in wfh_rows:
        writer.writerow(
            [
                "WFH Fixed-Rate",
                w.work_date.isoformat(),
                "D5-WFH",
                w.note or "Work from home",
                "",
                f"{w.hours:.2f}",
                f"{from_cents(round(w.hours * ATO_WFH_RATE_CENTS)):.2f}",
            ]
        )

    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="ato_deductions_{label}.csv"'},
    )
