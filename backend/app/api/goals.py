from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.engine.goals import GoalForecast, GoalSpec, forecast_goal
from app.models.finance import Account, FinancialGoal, GoalContribution
from app.schemas.finance import GoalContribute, GoalCreate, GoalOut, GoalUpdate
from app.services.savings import net_moved_by_account_id

router = APIRouter(prefix="/api/goals", tags=["goals"])


def _linked_moved(g: FinancialGoal, moved: dict[int, int]) -> int:
    """Money moved into the goal's linked savings account (never counted as negative progress)."""
    if g.linked_account_id is None:
        return 0
    return max(0, moved.get(g.linked_account_id, 0))


def goal_spec(g: FinancialGoal, moved: dict[int, int]) -> GoalSpec:
    return GoalSpec(
        goal_id=g.id,
        name=g.name,
        category=g.category,
        target_cents=g.target_cents,
        extra_costs_cents=g.extra_costs_cents,
        current_cents=g.current_cents + _linked_moved(g, moved),
        target_date=g.target_date,
        priority=g.priority,
        planned_contribution_cents=g.planned_contribution_cents,
        contribution_frequency=g.contribution_frequency,
    )


def goal_specs(db: Session) -> list[GoalSpec]:
    """All goals as specs (manual progress + linked savings), ordered by priority."""
    moved = net_moved_by_account_id(db)
    rows = db.scalars(select(FinancialGoal).order_by(FinancialGoal.priority, FinancialGoal.id)).all()
    return [goal_spec(g, moved) for g in rows]


def _to_out(db: Session, g: FinancialGoal, moved: dict[int, int]) -> GoalOut:
    forecast: GoalForecast = forecast_goal(goal_spec(g, moved), date.today())
    linked_name = None
    if g.linked_account_id is not None:
        acct = db.get(Account, g.linked_account_id)
        linked_name = acct.name if acct else None
    return GoalOut(
        **forecast.__dict__,
        linked_account_id=g.linked_account_id,
        linked_account_name=linked_name,
        linked_moved_cents=_linked_moved(g, moved),
    )


@router.get("", response_model=list[GoalOut])
def list_goals(db: Session = Depends(get_db)) -> list[GoalOut]:
    moved = net_moved_by_account_id(db)
    rows = db.scalars(select(FinancialGoal).order_by(FinancialGoal.priority, FinancialGoal.id)).all()
    return [_to_out(db, g, moved) for g in rows]


@router.post("", response_model=GoalOut, status_code=201)
def create_goal(payload: GoalCreate, db: Session = Depends(get_db)) -> GoalOut:
    if payload.linked_account_id is not None:
        linked = db.get(Account, payload.linked_account_id)
        if linked is None or linked.type != "savings":
            raise HTTPException(status_code=400, detail="Linked account must be a tracked savings account")

    goal = FinancialGoal(
        name=payload.name.strip(),
        category=payload.category,
        target_cents=payload.target_cents,
        extra_costs_cents=payload.extra_costs_cents,
        current_cents=payload.current_cents,
        target_date=payload.target_date,
        priority=payload.priority,
        planned_contribution_cents=payload.planned_contribution_cents,
        contribution_frequency=payload.contribution_frequency,
        linked_account_id=payload.linked_account_id,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return _to_out(db, goal, net_moved_by_account_id(db))


@router.post("/{goal_id}/contribute", response_model=GoalOut)
def contribute_to_goal(
    goal_id: int,
    payload: GoalContribute,
    db: Session = Depends(get_db),
) -> GoalOut:
    goal = db.get(FinancialGoal, goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    goal.current_cents = max(0, goal.current_cents + payload.amount_cents)
    db.add(
        GoalContribution(
            goal_id=goal.id,
            amount_cents=payload.amount_cents,
            date=date.today(),
            note=payload.note.strip(),
        )
    )
    db.commit()
    db.refresh(goal)
    return _to_out(db, goal, net_moved_by_account_id(db))


@router.patch("/{goal_id}", response_model=GoalOut)
def update_goal(
    goal_id: int,
    payload: GoalUpdate,
    db: Session = Depends(get_db),
) -> GoalOut:
    goal = db.get(FinancialGoal, goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    if payload.name is not None and payload.name.strip():
        goal.name = payload.name.strip()
    if payload.category is not None and payload.category.strip():
        goal.category = payload.category.strip()
    if payload.target_cents is not None and payload.target_cents > 0:
        goal.target_cents = payload.target_cents
    if payload.planned_contribution_cents is not None and payload.planned_contribution_cents >= 0:
        goal.planned_contribution_cents = payload.planned_contribution_cents
    if payload.clear_linked_account:
        goal.linked_account_id = None
    elif payload.linked_account_id is not None:
        linked = db.get(Account, payload.linked_account_id)
        if linked is None or linked.type != "savings":
            raise HTTPException(status_code=400, detail="Linked account must be a tracked savings account")
        goal.linked_account_id = payload.linked_account_id
    db.commit()
    db.refresh(goal)
    return _to_out(db, goal, net_moved_by_account_id(db))


@router.delete("/{goal_id}", status_code=204)
def delete_goal(goal_id: int, db: Session = Depends(get_db)) -> None:
    goal = db.get(FinancialGoal, goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    db.delete(goal)
    db.commit()
