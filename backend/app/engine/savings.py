import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Iterable

# CommBank app transfers between your own accounts look like:
#   "Transfer to xx0464 CommBank app"  /  "Transfer from xx3834 CommBank app"
_TRANSFER_RE = re.compile(r"^Transfer\s+(?:to|from)\s+(xx\d{4})\b", re.IGNORECASE)
MASK_RE = re.compile(r"^xx\d{4}$")


@dataclass(frozen=True)
class TransferCounterparty:
    mask: str
    count: int
    net_moved_in_cents: int  # money sent to that account minus money received back


def parse_transfer_mask(description_raw: str) -> str | None:
    """Return the lowercase xx#### of the other account in an internal transfer, if any."""
    m = _TRANSFER_RE.match(description_raw.strip())
    return m.group(1).lower() if m else None


def net_moved_by_mask(
    rows: Iterable[tuple[date, int, str]],
    start: date | None = None,
    end: date | None = None,
) -> dict[str, int]:
    """Net money moved INTO each counterpart account, from (date, amount_cents, description_raw).

    A negative amount on the spending account (a transfer out) means money moved in to the other account.
    """
    totals: dict[str, int] = defaultdict(int)
    for tx_date, amount_cents, description in rows:
        if start and tx_date < start:
            continue
        if end and tx_date > end:
            continue
        mask = parse_transfer_mask(description)
        if mask is None:
            continue
        totals[mask] += -amount_cents
    return dict(totals)


def suggest_transfer_counterparties(
    rows: Iterable[tuple[date, int, str]],
    tracked_masks: set[str],
) -> list[TransferCounterparty]:
    """Accounts you transfer to/from that are not tracked yet, most active first."""
    tracked = {m.lower() for m in tracked_masks}
    counts: dict[str, int] = defaultdict(int)
    nets: dict[str, int] = defaultdict(int)
    for _, amount_cents, description in rows:
        mask = parse_transfer_mask(description)
        if mask is None or mask in tracked:
            continue
        counts[mask] += 1
        nets[mask] += -amount_cents
    return sorted(
        (TransferCounterparty(m, counts[m], nets[m]) for m in counts),
        key=lambda x: x.count,
        reverse=True,
    )
