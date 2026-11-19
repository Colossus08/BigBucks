from collections import defaultdict
from dataclasses import dataclass
from datetime import date
import re
from typing import Iterable

from app.engine.budgeting import BudgetEvaluation
from app.engine.goals import GoalForecast
from app.engine.summary import SummaryResult


@dataclass(frozen=True)
class RecurringItem:
    merchant: str
    category_name: str
    occurrences: int
    avg_amount_cents: int
    estimated_cadence: str
    estimated_monthly_cents: int
    last_date: date


@dataclass(frozen=True)
class PriceHikeAlert:
    recurring_id: int
    merchant: str
    previous_cents: int
    new_cents: int
    delta_pct: float
    tx_date: date


@dataclass(frozen=True)
class FinancialInsight:
    severity: str  # info | warning | positive
    title: str
    observation: str
    evidence: str
    why_useful: str
    outcome: str


@dataclass(frozen=True)
class ForecastPoint:
    horizon: str
    months: int
    projected_cash_cents: int
    cumulative_income_cents: int
    cumulative_expenses_cents: int
    cumulative_goal_savings_cents: int


@dataclass(frozen=True)
class ScenarioComparison:
    baseline: list[ForecastPoint]
    alternative: list[ForecastPoint]
    five_year_difference_cents: int


COMMITMENT_CATEGORIES = {
    "Rent",
    "Utilities",
    "Internet",
    "Phone",
    "Insurance",
    "Loan repayments",
    "Credit card repayments",
    "Subscription services",
    "Other recurring payments",
    "Tithes & Offering",
}


def detect_recurring_payments(
    rows: Iterable[tuple[date, int, str, str, bool]],
) -> list[RecurringItem]:
    """Detect true recurring commitments from (date, amount_cents, merchant, category_name, is_transfer).

    Requires consistent amounts (within 15% of average), consistent cadence gaps,
    and excludes ad-hoc discretionary/person-to-person categories.
    """
    grouped: dict[tuple[str, str], list[tuple[date, int]]] = defaultdict(list)
    for tx_date, amount_cents, merchant, cat_name, is_transfer in rows:
        if is_transfer or amount_cents >= 0:
            continue
        if cat_name not in COMMITMENT_CATEGORIES:
            continue
        grouped[(merchant, cat_name)].append((tx_date, abs(amount_cents)))

    recurring: list[RecurringItem] = []
    for (merchant, cat_name), entries in grouped.items():
        if len(entries) < 2:
            continue
        entries.sort(key=lambda x: x[0])

        amounts = [e[1] for e in entries]
        avg_amount = round(sum(amounts) / len(amounts))
        if avg_amount <= 0:
            continue
        # Require amount consistency (within 15% of average)
        if any(abs(a - avg_amount) / avg_amount > 0.15 for a in amounts):
            continue

        gaps = [(entries[i][0] - entries[i - 1][0]).days for i in range(1, len(entries))]
        if all(5 <= g <= 9 for g in gaps) and len(entries) >= 3:
            cadence = "Weekly"
            monthly_est = round(avg_amount * 52 / 12)
        elif all(11 <= g <= 18 for g in gaps) and len(entries) >= 3:
            cadence = "Fortnightly"
            monthly_est = round(avg_amount * 26 / 12)
        elif all(24 <= g <= 36 for g in gaps):
            cadence = "Monthly"
            monthly_est = avg_amount
        else:
            continue

        recurring.append(
            RecurringItem(
                merchant=merchant,
                category_name=cat_name,
                occurrences=len(entries),
                avg_amount_cents=avg_amount,
                estimated_cadence=cadence,
                estimated_monthly_cents=monthly_est,
                last_date=entries[-1][0],
            )
        )

    return sorted(recurring, key=lambda x: x.estimated_monthly_cents, reverse=True)


def cadence_to_monthly_cents(amount_cents: int, cadence: str) -> int:
    c = cadence.lower()
    if c == "weekly":
        return round(amount_cents * 52 / 12)
    if c == "fortnightly":
        return round(amount_cents * 26 / 12)
    return amount_cents


_REF_TOKEN_RE = re.compile(r"\b(?:P[0-9A-F]{6,}|[0-9]{4,}|[A-Z0-9]*\d[A-Z0-9]{5,})\b", re.IGNORECASE)
_CITY_SUFFIX_RE = re.compile(
    r"\s+(?:SYDNEY|MELBOURNE|NORTH SYDNEY|BARANGAROO|POINT COOK|WERRIBEE|FOOTSCRAY|DOCKLANDS|TARNEIT|BELLEVUE|NS|VI|VIC|NSW|WA|USA)$",
    re.IGNORECASE,
)


def _canonical_merchant(merchant: str) -> str:
    cleaned = _REF_TOKEN_RE.sub("", merchant)
    cleaned = " ".join(cleaned.split())
    for _ in range(3):
        next_cleaned = _CITY_SUFFIX_RE.sub("", cleaned).strip()
        if next_cleaned == cleaned:
            break
        cleaned = next_cleaned
    return cleaned or merchant


def suggest_recurring_candidates(
    rows: Iterable[tuple[date, int, str, str, bool]],
    already_saved_merchants: set[str],
) -> list[RecurringItem]:
    """Suggest periodic payments for user review (more permissive than auto-confirmed commitments)."""
    grouped: dict[tuple[str, str], list[tuple[date, int]]] = defaultdict(list)
    saved_upper = {_canonical_merchant(m).upper() for m in already_saved_merchants}

    for tx_date, amount_cents, merchant, cat_name, is_transfer in rows:
        if is_transfer or amount_cents >= 0:
            continue
        canon = _canonical_merchant(merchant).upper()
        if canon in saved_upper or merchant.upper() in saved_upper:
            continue
        grouped[(canon, cat_name)].append((tx_date, abs(amount_cents)))

    suggestions: list[RecurringItem] = []
    for (merchant, cat_name), entries in grouped.items():
        if len(entries) < 2:
            continue
        entries.sort(key=lambda x: x[0])
        gaps = [(entries[i][0] - entries[i - 1][0]).days for i in range(1, len(entries))]
        avg_gap = sum(gaps) / len(gaps)
        avg_amount = round(sum(e[1] for e in entries) / len(entries))

        if 5 <= avg_gap <= 10:
            cadence = "Weekly"
        elif 11 <= avg_gap <= 19:
            cadence = "Fortnightly"
        elif 20 <= avg_gap <= 40:
            cadence = "Monthly"
        else:
            continue

        suggestions.append(
            RecurringItem(
                merchant=merchant,
                category_name=cat_name,
                occurrences=len(entries),
                avg_amount_cents=avg_amount,
                estimated_cadence=cadence,
                estimated_monthly_cents=cadence_to_monthly_cents(avg_amount, cadence),
                last_date=entries[-1][0],
            )
        )

    return sorted(suggestions, key=lambda x: (x.occurrences, x.estimated_monthly_cents), reverse=True)


def detect_price_hikes(
    confirmed_recurring: Iterable[tuple[int, str, str, int]],
    transactions: Iterable[tuple[date, int, str, str]],
) -> list[PriceHikeAlert]:
    """Scan transactions against confirmed recurring payments for price hikes (§4.2).

    confirmed_recurring: (id, merchant, merchant_pattern, baseline_amount_cents)
    transactions: (tx_date, amount_cents, merchant, description_raw)
    """
    tx_list = [t for t in transactions if t[1] < 0]
    alerts: list[PriceHikeAlert] = []

    for rec_id, rec_merchant, rec_pattern, baseline_cents in confirmed_recurring:
        if baseline_cents <= 0:
            continue
        needle = (rec_pattern or rec_merchant).strip().upper()
        canon_needle = _canonical_merchant(needle).upper()
        if not needle:
            continue

        matching = [
            (tx_date, abs(amt))
            for tx_date, amt, m, desc in tx_list
            if needle in m.upper()
            or needle in desc.upper()
            or (canon_needle and canon_needle == _canonical_merchant(m).upper())
        ]
        if not matching:
            continue
        matching.sort(key=lambda x: x[0])
        latest_date, latest_cents = matching[-1]
        if latest_cents > baseline_cents:
            delta_pct = round((latest_cents - baseline_cents) / baseline_cents * 100.0, 1)
            alerts.append(
                PriceHikeAlert(
                    recurring_id=rec_id,
                    merchant=rec_merchant,
                    previous_cents=baseline_cents,
                    new_cents=latest_cents,
                    delta_pct=delta_pct,
                    tx_date=latest_date,
                )
            )
    return alerts


def generate_insights(
    summary: SummaryResult,
    budget_evals: list[BudgetEvaluation],
    recurring: list[RecurringItem],
    goals: list[GoalForecast],
) -> list[FinancialInsight]:
    """Generate transparent, explainable financial insights (§11.4)."""
    insights: list[FinancialInsight] = []

    for b in budget_evals:
        if b.status in {"over", "warning"}:
            insights.append(
                FinancialInsight(
                    severity="warning",
                    title=f"{b.category_name} budget at {b.pct_used}%",
                    observation=f"You have spent ${b.spent_cents / 100:,.2f} of your ${b.limit_cents / 100:,.2f} {b.category_name} budget.",
                    evidence=f"Current pace projects ${b.projected_cents / 100:,.2f} by period end.",
                    why_useful="Catching budget drift early lets you adjust discretionary spending before the end of the cycle.",
                    outcome=f"Staying within limit preserves ${max(0, b.limit_cents - b.spent_cents) / 100:,.2f} for your goals.",
                )
            )

    if recurring:
        total_rec = sum(r.estimated_monthly_cents for r in recurring)
        insights.append(
            FinancialInsight(
                severity="info",
                title=f"{len(recurring)} recurring commitments active",
                observation=f"Confirmed recurring payments total ${total_rec / 100:,.2f}/month.",
                evidence=f"Top commitment: {recurring[0].merchant} (${recurring[0].avg_amount_cents / 100:,.2f} {recurring[0].estimated_cadence.lower()}).",
                why_useful="These commitments are reserved from Available Cash and included in your pay-cycle plan.",
                outcome="Keeping recurring bills accurate ensures your discretionary balance is reliable.",
            )
        )

    if summary.income_cents > 0 and summary.net_savings_cents < 0:
        insights.append(
            FinancialInsight(
                severity="warning",
                title="Spending exceeded income this period",
                observation=f"Net cash flow was -${abs(summary.net_savings_cents) / 100:,.2f}.",
                evidence=f"Income ${summary.income_cents / 100:,.2f} vs net expenses ${summary.expenses_cents / 100:,.2f}.",
                why_useful="Identifying deficit periods helps you rebalance variable spending or draw intentionally from savings.",
                outcome="Trimming discretionary categories brings cash flow back into surplus.",
            )
        )

    if goals:
        top_goal = goals[0]
        if top_goal.projected_completion_date:
            insights.append(
                FinancialInsight(
                    severity="info",
                    title=f"Priority #1 goal ({top_goal.name}) on track for {top_goal.projected_completion_date}",
                    observation=f"{top_goal.name} is {top_goal.completion_pct}% complete (${top_goal.current_cents / 100:,.2f} / ${top_goal.total_target_cents / 100:,.2f}).",
                    evidence=f"Planned contribution: ${top_goal.planned_contribution_cents / 100:,.2f} {top_goal.contribution_frequency}.",
                    why_useful="Tracking projected dates makes trade-offs between simultaneous goals concrete.",
                    outcome=f"Remaining needed: ${top_goal.remaining_cents / 100:,.2f}.",
                )
            )

    return insights


def forecast_cashflow(
    starting_cash_cents: int,
    monthly_income_cents: int,
    monthly_expenses_cents: int,
    monthly_goal_savings_cents: int,
) -> list[ForecastPoint]:
    """Project cash position across 3m, 6m, 12m, and 5y horizons (§13.3)."""
    horizons = [("3 Months", 3), ("6 Months", 6), ("12 Months", 12), ("5 Years", 60)]
    monthly_net = monthly_income_cents - monthly_expenses_cents
    points: list[ForecastPoint] = []
    for label, m in horizons:
        points.append(
            ForecastPoint(
                horizon=label,
                months=m,
                projected_cash_cents=starting_cash_cents + monthly_net * m,
                cumulative_income_cents=monthly_income_cents * m,
                cumulative_expenses_cents=monthly_expenses_cents * m,
                cumulative_goal_savings_cents=monthly_goal_savings_cents * m,
            )
        )
    return points


def compare_scenarios(
    starting_cash_cents: int,
    monthly_income_cents: int,
    monthly_expenses_cents: int,
    monthly_goal_savings_cents: int,
    extra_monthly_savings_cents: int,
    monthly_income_delta_cents: int = 0,
) -> ScenarioComparison:
    """Compare baseline vs what-if cash flow scenario (§13.4)."""
    baseline = forecast_cashflow(
        starting_cash_cents,
        monthly_income_cents,
        monthly_expenses_cents,
        monthly_goal_savings_cents,
    )
    alt_expenses = max(0, monthly_expenses_cents - extra_monthly_savings_cents)
    alternative = forecast_cashflow(
        starting_cash_cents,
        monthly_income_cents + monthly_income_delta_cents,
        alt_expenses,
        monthly_goal_savings_cents + extra_monthly_savings_cents,
    )
    diff_5y = alternative[-1].projected_cash_cents - baseline[-1].projected_cash_cents
    return ScenarioComparison(
        baseline=baseline,
        alternative=alternative,
        five_year_difference_cents=diff_5y,
    )
