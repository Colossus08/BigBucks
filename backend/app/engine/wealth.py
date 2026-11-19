from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable


@dataclass(frozen=True)
class HoldingSpec:
    holding_id: int
    symbol: str
    name: str
    asset_type: str
    units_milli: int
    avg_cost_cents: int
    current_price_cents: int


@dataclass(frozen=True)
class HoldingValuation:
    holding_id: int
    symbol: str
    name: str
    asset_type: str
    units: Decimal
    cost_basis_cents: int
    market_value_cents: int
    gain_loss_cents: int
    gain_loss_pct: Decimal


@dataclass(frozen=True)
class PortfolioSummary:
    total_cost_cents: int
    total_value_cents: int
    total_gain_loss_cents: int
    holdings: list[HoldingValuation]


@dataclass(frozen=True)
class SuperProjectionPoint:
    years: int
    projected_balance_cents: int


def evaluate_portfolio(holdings: Iterable[HoldingSpec]) -> PortfolioSummary:
    """Calculate portfolio market value, cost basis, and unrealised gain/loss."""
    items: list[HoldingValuation] = []
    total_cost = 0
    total_val = 0

    for h in holdings:
        units = Decimal(h.units_milli) / Decimal("1000")
        cost_basis = round(h.units_milli * h.avg_cost_cents / 1000)
        market_value = round(h.units_milli * h.current_price_cents / 1000)
        gain_loss = market_value - cost_basis
        gain_pct = (
            (Decimal(gain_loss) / Decimal(cost_basis) * Decimal("100")).quantize(Decimal("0.1"))
            if cost_basis > 0
            else Decimal("0.0")
        )
        total_cost += cost_basis
        total_val += market_value
        items.append(
            HoldingValuation(
                holding_id=h.holding_id,
                symbol=h.symbol,
                name=h.name,
                asset_type=h.asset_type,
                units=units,
                cost_basis_cents=cost_basis,
                market_value_cents=market_value,
                gain_loss_cents=gain_loss,
                gain_loss_pct=gain_pct,
            )
        )

    return PortfolioSummary(
        total_cost_cents=total_cost,
        total_value_cents=total_val,
        total_gain_loss_cents=total_val - total_cost,
        holdings=items,
    )


def project_superannuation(
    starting_balance_cents: int,
    annual_employer_cents: int,
    personal_monthly_cents: int,
    expected_return_bps: int,
    horizons: tuple[int, ...] = (5, 10, 20, 30),
) -> list[SuperProjectionPoint]:
    """Compound monthly superannuation growth projection (explicitly assumption-based)."""
    annual_rate = expected_return_bps / 10000.0
    monthly_rate = annual_rate / 12.0
    monthly_contrib = (annual_employer_cents / 12.0) + personal_monthly_cents

    max_years = max(horizons)
    balance = float(starting_balance_cents)
    results: dict[int, int] = {}

    for month in range(1, max_years * 12 + 1):
        balance = balance * (1.0 + monthly_rate) + monthly_contrib
        if month % 12 == 0 and (month // 12) in horizons:
            results[month // 12] = round(balance)

    return [SuperProjectionPoint(years=y, projected_balance_cents=results[y]) for y in horizons]
