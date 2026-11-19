from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
import math


@dataclass(frozen=True)
class GoalSpec:
    goal_id: int
    name: str
    category: str
    target_cents: int
    extra_costs_cents: int
    current_cents: int
    target_date: date | None
    priority: int
    planned_contribution_cents: int
    contribution_frequency: str


@dataclass(frozen=True)
class GoalForecast:
    goal_id: int
    name: str
    category: str
    total_target_cents: int
    target_cents: int
    extra_costs_cents: int
    current_cents: int
    remaining_cents: int
    completion_pct: Decimal
    target_date: date | None
    priority: int
    planned_contribution_cents: int
    contribution_frequency: str
    required_weekly_cents: int | None
    required_fortnightly_cents: int | None
    required_monthly_cents: int | None
    projected_completion_date: date | None


def contribution_to_fortnightly_cents(amount_cents: int, frequency: str) -> int:
    if frequency == "weekly":
        return amount_cents * 2
    if frequency == "monthly":
        return round(amount_cents * 12 / 26)
    return amount_cents


def forecast_goal(goal: GoalSpec, anchor: date) -> GoalForecast:
    """Compute progress, required contributions to hit target_date, and projected completion date."""
    total_target = goal.target_cents + goal.extra_costs_cents
    remaining = max(0, total_target - goal.current_cents)
    completion_pct = (
        min(Decimal("100.0"), (Decimal(goal.current_cents) / Decimal(total_target) * Decimal("100")).quantize(Decimal("0.1")))
        if total_target > 0
        else Decimal("100.0")
    )

    req_weekly = req_fortnightly = req_monthly = None
    if goal.target_date and goal.target_date > anchor and remaining > 0:
        days_left = (goal.target_date - anchor).days
        weeks_left = max(1.0, days_left / 7.0)
        fortnights_left = max(1.0, days_left / 14.0)
        months_left = max(1.0, days_left / 30.4375)
        req_weekly = math.ceil(remaining / weeks_left)
        req_fortnightly = math.ceil(remaining / fortnights_left)
        req_monthly = math.ceil(remaining / months_left)

    projected_date: date | None = None
    if remaining == 0:
        projected_date = anchor
    elif goal.planned_contribution_cents > 0:
        days_per_step = 7 if goal.contribution_frequency == "weekly" else 30 if goal.contribution_frequency == "monthly" else 14
        steps = math.ceil(remaining / goal.planned_contribution_cents)
        projected_date = anchor + timedelta(days=steps * days_per_step)

    return GoalForecast(
        goal_id=goal.goal_id,
        name=goal.name,
        category=goal.category,
        total_target_cents=total_target,
        target_cents=goal.target_cents,
        extra_costs_cents=goal.extra_costs_cents,
        current_cents=goal.current_cents,
        remaining_cents=remaining,
        completion_pct=completion_pct,
        target_date=goal.target_date,
        priority=goal.priority,
        planned_contribution_cents=goal.planned_contribution_cents,
        contribution_frequency=goal.contribution_frequency,
        required_weekly_cents=req_weekly,
        required_fortnightly_cents=req_fortnightly,
        required_monthly_cents=req_monthly,
        projected_completion_date=projected_date,
    )
