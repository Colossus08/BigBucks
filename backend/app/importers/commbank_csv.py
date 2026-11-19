import csv
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import io
import re

from app.engine.money import to_cents

VALUE_DATE_RE = re.compile(r"\s+Value Date:\s*\d{2}/\d{2}/\d{4}", re.IGNORECASE)
CARD_SUFFIX_RE = re.compile(r"\s+Card\s+xx\d{4}", re.IGNORECASE)
SQ_PREFIX_RE = re.compile(r"^SQ\s*\*\s*", re.IGNORECASE)
FAST_TRANSFER_FROM_RE = re.compile(
    r"^Fast Transfer From\s+(?:-\s*)?(.+?)\s+to\s+PayID\b", re.IGNORECASE
)
TRANSFER_TO_PERSON_RE = re.compile(
    r"^Transfer\s+To\s+(.+?)\s+(?:-\s*\$?\d+.*?\s+)?(?:PayID|from\s+CommBank|CommBank\s+App)\b",
    re.IGNORECASE,
)
INTERNAL_TRANSFER_RE = re.compile(
    r"^Transfer\s+(?:to|from)\s+(xx\d{4})\b", re.IGNORECASE
)
TRAILING_COUNTRY_RE = re.compile(r"\s+(?:VICAU|NSWAU|QLDAU|SAAU|WAAU|AU)$")


@dataclass(frozen=True)
class ParsedRow:
    row_number: int
    tx_date: date
    amount_cents: int
    description_raw: str
    merchant: str
    balance_cents: int | None


@dataclass
class ParseError:
    row_number: int
    raw_line: str
    reason: str


@dataclass
class ParseResult:
    rows: list[ParsedRow] = field(default_factory=list)
    errors: list[ParseError] = field(default_factory=list)
    balance_warnings: list[str] = field(default_factory=list)


def normalise_merchant(description_raw: str) -> str:
    """Extract a clean, consistent merchant or counterparty name from a CommBank description."""
    desc = " ".join(description_raw.strip().split())

    internal_match = INTERNAL_TRANSFER_RE.match(desc)
    if internal_match:
        return f"Transfer {internal_match.group(1).lower()}"

    fast_match = FAST_TRANSFER_FROM_RE.match(desc)
    if fast_match:
        return fast_match.group(1).strip(" -").upper()

    to_person_match = TRANSFER_TO_PERSON_RE.match(desc)
    if to_person_match:
        return to_person_match.group(1).strip(" -").upper()

    cleaned = VALUE_DATE_RE.sub("", desc)
    cleaned = CARD_SUFFIX_RE.sub("", cleaned)
    cleaned = SQ_PREFIX_RE.sub("", cleaned)
    cleaned = TRAILING_COUNTRY_RE.sub("", cleaned)
    cleaned = cleaned.strip(" *-")

    return cleaned.upper() if cleaned else desc.upper()


def compute_dedupe_hash(
    account_id: int,
    tx_date: date,
    amount_cents: int,
    description_raw: str,
    balance_cents: int | None,
) -> str:
    """Create a deterministic SHA-256 hash so re-importing overlapping CSVs is idempotent."""
    payload = f"{account_id}|{tx_date.isoformat()}|{amount_cents}|{description_raw.strip()}|{balance_cents}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _parse_amount_cents(raw: str) -> int:
    cleaned = raw.strip().replace("$", "").replace(",", "")
    return to_cents(Decimal(cleaned))


def _looks_like_header(row: list[str]) -> bool:
    if not row:
        return False
    first = row[0].strip().lower()
    return first in {"date", "transaction date"}


def parse_commbank_csv(content: str) -> ParseResult:
    """Parse a CommBank NetBank CSV export (headerless or with header)."""
    result = ParseResult()
    reader = csv.reader(io.StringIO(content.lstrip("\ufeff")))

    for idx, row in enumerate(reader, start=1):
        if not row or all(not cell.strip() for cell in row):
            continue
        if idx == 1 and _looks_like_header(row):
            continue
        if len(row) < 3:
            result.errors.append(ParseError(idx, ",".join(row), "Expected at least 3 columns"))
            continue

        raw_date, raw_amount, raw_desc = row[0].strip(), row[1].strip(), row[2].strip()
        raw_balance = row[3].strip() if len(row) >= 4 else ""

        try:
            tx_date = datetime.strptime(raw_date, "%d/%m/%Y").date()
        except ValueError:
            result.errors.append(ParseError(idx, ",".join(row), f"Invalid date: {raw_date!r}"))
            continue

        try:
            amount_cents = _parse_amount_cents(raw_amount)
        except (InvalidOperation, ValueError):
            result.errors.append(ParseError(idx, ",".join(row), f"Invalid amount: {raw_amount!r}"))
            continue

        balance_cents: int | None = None
        if raw_balance:
            try:
                balance_cents = _parse_amount_cents(raw_balance)
            except (InvalidOperation, ValueError):
                result.errors.append(ParseError(idx, ",".join(row), f"Invalid balance: {raw_balance!r}"))
                continue

        result.rows.append(
            ParsedRow(
                row_number=idx,
                tx_date=tx_date,
                amount_cents=amount_cents,
                description_raw=raw_desc,
                merchant=normalise_merchant(raw_desc),
                balance_cents=balance_cents,
            )
        )

    result.balance_warnings = check_running_balance_continuity(result.rows)
    return result


def check_running_balance_continuity(rows: list[ParsedRow]) -> list[str]:
    """Verify running balances across consecutive rows in a reverse-chronological CommBank export."""
    with_bal = [r for r in rows if r.balance_cents is not None]
    if len(with_bal) < 2:
        return []

    warnings: list[str] = []
    # CommBank exports are newest-first: newer.balance == older.balance + newer.amount
    for i in range(len(with_bal) - 1):
        newer = with_bal[i]
        older = with_bal[i + 1]
        expected_newer = (older.balance_cents or 0) + newer.amount_cents
        actual_newer = newer.balance_cents or 0
        diff = actual_newer - expected_newer
        if diff != 0:
            warnings.append(
                f"Row {newer.row_number} ({newer.tx_date.isoformat()}): expected balance "
                f"${expected_newer / 100:,.2f} from prior row, found ${actual_newer / 100:,.2f} "
                f"(gap ${diff / 100:+,.2f})."
            )
            if len(warnings) >= 5:
                break
    return warnings
