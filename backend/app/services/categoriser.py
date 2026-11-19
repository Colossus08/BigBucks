from collections import Counter
from dataclasses import dataclass
import re
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.finance import Category, MerchantRule, RecurringPayment, Transaction

INTERNAL_TRANSFER_DESC_RE = re.compile(
    r"^Transfer\s+(?:to|from)\s+(xx\d{4})\s+CommBank\s+app\b", re.IGNORECASE
)

BILL_KEYWORDS_RE = re.compile(
    r"\b(BILL|BILLS|UTILITY|UTILITIES|ELEC|ELECTRICITY|WATER|GAS|WIFI|INTERNET|NBN)\b",
    re.IGNORECASE,
)
RENT_KEYWORDS_RE = re.compile(
    r"\b(RENT|BOARD|LEASE)\b",
    re.IGNORECASE,
)

# Any transfer matched to Rent by a generic merchant rule that is below $200 and
# does not explicitly say "rent" in the description is treated as a shared bill/utility.
DEFAULT_MIN_RENT_CENTS = 20000


@dataclass(frozen=True)
class CategorisationResult:
    category_id: int | None
    is_transfer: bool
    category_source: str


def _matches_rule(rule: MerchantRule, merchant: str, description_raw: str) -> bool:
    haystack_merchant = merchant.upper()
    haystack_desc = description_raw.upper()
    pattern = rule.pattern.strip()

    if rule.match_type == "exact":
        return haystack_merchant == pattern.upper()
    if rule.match_type == "regex":
        return bool(
            re.search(pattern, haystack_desc, re.IGNORECASE)
            or re.search(pattern, haystack_merchant, re.IGNORECASE)
        )
    # Default ("contains"): use word-boundary matching for short single-word tokens
    # so e.g. "IGA" or "BP" cannot match inside unrelated words like "NAVIGATION".
    p_upper = pattern.upper()
    p_stripped = p_upper.strip()
    if p_stripped.isalnum() and len(p_stripped) <= 5:
        word_re = rf"\b{re.escape(p_stripped)}\b"
        return bool(re.search(word_re, haystack_merchant) or re.search(word_re, haystack_desc))
    return p_upper in haystack_merchant or p_upper in haystack_desc


def _resolve_rent_vs_utilities(
    matched_cat: Category | None,
    description_raw: str,
    amount_cents: int,
    categories_by_id: dict[int, Category],
    min_rent_cents: int = DEFAULT_MIN_RENT_CENTS,
) -> int | None:
    """If a rule resolves to 'Rent', check description keywords and amount threshold
    so small bill payments (e.g. $50 to landlord/housemate) go to 'Utilities' instead."""
    if matched_cat is None:
        return None
    if matched_cat.name != "Rent":
        return matched_cat.id

    utilities_cat = next((c for c in categories_by_id.values() if c.name == "Utilities"), None)
    if utilities_cat is None:
        return matched_cat.id

    has_bill_kw = bool(BILL_KEYWORDS_RE.search(description_raw))
    has_rent_kw = bool(RENT_KEYWORDS_RE.search(description_raw))

    if has_bill_kw and not has_rent_kw:
        return utilities_cat.id
    if not has_rent_kw and 0 < abs(amount_cents) < min_rent_cents:
        return utilities_cat.id
    return matched_cat.id


def categorise_transaction(
    description_raw: str,
    merchant: str,
    amount_cents: int,
    rules: list[MerchantRule],
    transfer_category_id: int | None,
    uncategorised_category_id: int | None,
    categories_by_id: dict[int, Category],
    min_rent_cents: int = DEFAULT_MIN_RENT_CENTS,
) -> CategorisationResult:
    """Determine category and transfer flag for a transaction.

    Priority:
    1. Specific regex/keyword rules in description (e.g. 'Transfer To Fauzi.*bills')
    2. Learned user rules (lowest priority number first, source == 'learned')
    3. Internal CommBank app transfers (Transfer to/from xx#### CommBank app)
    4. Seeded rules (ordered by priority)
    5. Uncategorised fallback
    """
    sorted_rules = sorted((r for r in rules if r.is_active), key=lambda r: r.priority)

    # 1. Learned rules first (with smart Rent vs Utilities distinction)
    for rule in sorted_rules:
        if rule.source == "learned" and _matches_rule(rule, merchant, description_raw):
            cat = categories_by_id.get(rule.category_id)
            resolved_id = _resolve_rent_vs_utilities(
                cat, description_raw, amount_cents, categories_by_id, min_rent_cents
            )
            resolved_cat = categories_by_id.get(resolved_id) if resolved_id else cat
            is_transfer = bool(resolved_cat and resolved_cat.group == "Transfer")
            return CategorisationResult(resolved_id, is_transfer, "rule")

    # 2. Internal CommBank account transfer detection
    if INTERNAL_TRANSFER_DESC_RE.match(description_raw.strip()):
        return CategorisationResult(transfer_category_id, True, "rule")

    # 3. Seeded rules (respecting income vs expense sign when category is income)
    for rule in sorted_rules:
        if rule.source == "learned":
            continue
        cat = categories_by_id.get(rule.category_id)
        if cat and cat.is_income and amount_cents <= 0:
            continue
        if _matches_rule(rule, merchant, description_raw):
            resolved_id = _resolve_rent_vs_utilities(
                cat, description_raw, amount_cents, categories_by_id, min_rent_cents
            )
            resolved_cat = categories_by_id.get(resolved_id) if resolved_id else cat
            is_transfer = bool(resolved_cat and resolved_cat.group == "Transfer")
            return CategorisationResult(resolved_id, is_transfer, "rule")

    return CategorisationResult(uncategorised_category_id, False, "default")


def apply_learned_merchant_rule(
    db: Session,
    merchant: str,
    category_id: int,
) -> int:
    """Create or update an exact learned rule for a merchant and re-apply to matching transactions."""
    cat = db.get(Category, category_id)
    if cat is None:
        raise ValueError(f"Category {category_id} not found")

    existing = db.scalar(
        select(MerchantRule).where(
            MerchantRule.source == "learned",
            MerchantRule.match_type == "exact",
            MerchantRule.pattern == merchant.upper(),
        )
    )
    if existing:
        existing.category_id = category_id
        existing.is_active = True
    else:
        db.add(
            MerchantRule(
                pattern=merchant.upper(),
                match_type="exact",
                category_id=category_id,
                priority=10,
                source="learned",
                is_active=True,
            )
        )

    categories_by_id = {c.id: c for c in db.scalars(select(Category)).all()}
    is_transfer = cat.group == "Transfer"
    txs = db.scalars(select(Transaction).where(Transaction.merchant == merchant)).all()
    for tx in txs:
        resolved_id = _resolve_rent_vs_utilities(
            cat, tx.description_raw, tx.amount_cents, categories_by_id
        )
        tx.category_id = resolved_id or category_id
        tx.is_transfer = is_transfer
        tx.category_source = "user"

    db.flush()
    reconcile_rent_transactions(db)
    return len(txs)


def split_transaction(
    db: Session,
    tx: Transaction,
    split_amount_cents: int,
    split_category_id: int,
    note: str = "",
) -> Transaction:
    """Split `split_amount_cents` (positive integer representing expense magnitude)
    out of `tx` into a new linked child transaction on the same date & account."""
    total_abs = abs(tx.amount_cents)
    if split_amount_cents <= 0 or split_amount_cents >= total_abs:
        raise ValueError("Split amount must be between $0.01 and the total transaction amount")

    split_cat = db.get(Category, split_category_id)
    if split_cat is None:
        raise ValueError("Target category for split not found")

    sign = -1 if tx.amount_cents < 0 else 1
    remaining_abs = total_abs - split_amount_cents
    tx.amount_cents = sign * remaining_abs

    suffix = f" [Split: {note.strip()}]" if note.strip() else f" [Split: {split_cat.name}]"
    child_hash = f"{tx.dedupe_hash}:split:{uuid.uuid4().hex[:8]}"
    child = Transaction(
        account_id=tx.account_id,
        import_batch_id=tx.import_batch_id,
        date=tx.date,
        amount_cents=sign * split_amount_cents,
        description_raw=f"{tx.description_raw}{suffix}",
        merchant=tx.merchant,
        balance_cents=None,
        category_id=split_cat.id,
        kind=tx.kind,
        is_transfer=split_cat.group == "Transfer",
        dedupe_hash=child_hash,
        category_source="user",
    )
    db.add(child)
    db.flush()
    return child


def unsplit_transaction(db: Session, child_tx: Transaction) -> Transaction:
    """Merge a split child transaction back into its parent transaction."""
    if ":split:" not in child_tx.dedupe_hash:
        raise ValueError("Transaction is not a split item")
    parent_hash = child_tx.dedupe_hash.split(":split:")[0]
    parent = db.scalar(select(Transaction).where(Transaction.dedupe_hash == parent_hash))
    if parent is None:
        # Fallback: same account, date, merchant
        parent = db.scalar(
            select(Transaction).where(
                Transaction.account_id == child_tx.account_id,
                Transaction.date == child_tx.date,
                Transaction.merchant == child_tx.merchant,
                Transaction.id != child_tx.id,
            )
        )
    if parent is None:
        raise ValueError("Original parent transaction not found")

    parent.amount_cents += child_tx.amount_cents
    db.delete(child_tx)
    db.flush()
    return parent


def reconcile_rent_transactions(db: Session) -> int:
    """Ensure Rent transactions respect description keywords and fixed Rent baselines:
    1. Any transaction in 'Rent' with bill keywords (and no 'rent' keyword) or below the
       minimum rent threshold ($200 or <50% of fixed rent) is moved to 'Utilities'.
    2. Any unsplit 'Rent' transaction that exceeds the fixed Rent amount for that merchant
       automatically splits the excess remainder into 'Utilities'.
    """
    rent_cat = db.scalar(select(Category).where(Category.name == "Rent"))
    utilities_cat = db.scalar(select(Category).where(Category.name == "Utilities"))
    if rent_cat is None or utilities_cat is None:
        return 0

    rec_rows = list(
        db.scalars(
            select(RecurringPayment).where(RecurringPayment.cadence != "Dismissed")
        ).all()
    )
    rent_recurrings = [
        r for r in rec_rows if r.category_name.lower() == "rent" and r.amount_cents >= DEFAULT_MIN_RENT_CENTS
    ]

    rent_txs = list(
        db.scalars(
            select(Transaction).where(
                Transaction.category_id == rent_cat.id,
                Transaction.amount_cents < 0,
            )
        ).all()
    )
    if not rent_txs:
        return 0

    # Determine fixed rent baseline per merchant:
    # 1. Explicit RecurringPayment in category "Rent" matching the merchant
    # 2. Otherwise, if a merchant has multiple rent-sized payments (>= $200) where a repeated mode exists
    fixed_rent_by_merchant: dict[str, int] = {}
    for r in rent_recurrings:
        fixed_rent_by_merchant[r.merchant.upper()] = r.amount_cents

    by_merchant_amounts: dict[str, list[int]] = {}
    for tx in rent_txs:
        amt = abs(tx.amount_cents)
        if amt >= DEFAULT_MIN_RENT_CENTS and not (
            BILL_KEYWORDS_RE.search(tx.description_raw) and not RENT_KEYWORDS_RE.search(tx.description_raw)
        ):
            by_merchant_amounts.setdefault(tx.merchant.upper(), []).append(amt)

    for m_upper, amts in by_merchant_amounts.items():
        if m_upper in fixed_rent_by_merchant:
            continue
        counts = Counter(amts)
        # If there is a clear repeated rent amount (occurring >= 2 times), treat the minimum repeated mode as fixed rent
        repeated = [amt for amt, cnt in counts.items() if cnt >= 2]
        if repeated:
            fixed_rent_by_merchant[m_upper] = min(repeated)

    changed = 0
    for tx in rent_txs:
        if ":split:" in tx.dedupe_hash or tx.category_source == "manual":
            continue
        amt = abs(tx.amount_cents)
        m_upper = tx.merchant.upper()
        fixed_rent = fixed_rent_by_merchant.get(m_upper)
        # Also match if any rent recurring pattern is a substring of merchant/description
        if fixed_rent is None:
            for r in rent_recurrings:
                needle = (r.merchant_pattern or r.merchant).strip().upper()
                if needle and (needle in m_upper or needle in tx.description_raw.upper()):
                    fixed_rent = r.amount_cents
                    break

        has_bill_kw = bool(BILL_KEYWORDS_RE.search(tx.description_raw))
        has_rent_kw = bool(RENT_KEYWORDS_RE.search(tx.description_raw))

        # Case 1: Bill keyword (without 'rent') OR small bill payment below threshold
        min_threshold = max(DEFAULT_MIN_RENT_CENTS, int(fixed_rent * 0.5)) if fixed_rent else DEFAULT_MIN_RENT_CENTS
        if (has_bill_kw and not has_rent_kw) or (not has_rent_kw and amt < min_threshold):
            tx.category_id = utilities_cat.id
            tx.is_transfer = False
            changed += 1
            continue

        # Case 2: Combined payment exceeding fixed Rent amount -> auto-split remainder to Utilities
        if fixed_rent and amt > fixed_rent:
            # Check if already split for this transaction
            existing_split = db.scalar(
                select(Transaction).where(
                    Transaction.dedupe_hash.like(f"{tx.dedupe_hash}:split:%")
                )
            )
            if existing_split is None:
                remainder_cents = amt - fixed_rent
                split_transaction(
                    db=db,
                    tx=tx,
                    split_amount_cents=remainder_cents,
                    split_category_id=utilities_cat.id,
                    note="Bill remainder above fixed Rent",
                )
                changed += 1

    if changed > 0:
        db.flush()
    return changed
