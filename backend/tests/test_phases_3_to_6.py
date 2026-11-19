from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.engine.budgeting import BudgetSpec, evaluate_budgets
from app.engine.goals import GoalSpec, forecast_goal
from app.engine.insights import compare_scenarios, detect_recurring_payments, suggest_recurring_candidates
from app.engine.summary import TransactionRecord
from app.engine.wealth import HoldingSpec, evaluate_portfolio, project_superannuation
from app.main import app
from app.seed import seed_defaults


def test_budget_evaluation_and_warning_status() -> None:
    specs = [BudgetSpec(1, 10, "Groceries", "Essential", "monthly", 50000)]
    records = [
        TransactionRecord(date(2026, 11, 2), -20000, 10, "Groceries", "Essential", False),
        TransactionRecord(date(2026, 11, 5), -22000, 10, "Groceries", "Essential", False),
    ]
    evals = evaluate_budgets(specs, records, date(2026, 11, 15))
    assert len(evals) == 1
    assert evals[0].spent_cents == 42000
    assert evals[0].pct_used == Decimal("84.0")
    assert evals[0].status == "warning"


def test_goal_forecast_with_extra_costs() -> None:
    goal = GoalSpec(
        goal_id=1,
        name="Car",
        category="car",
        target_cents=1000000,
        extra_costs_cents=200000,
        current_cents=200000,
        target_date=date(2027, 11, 18),
        priority=1,
        planned_contribution_cents=25000,
        contribution_frequency="fortnightly",
    )
    res = forecast_goal(goal, date(2026, 11, 18))
    assert res.total_target_cents == 1200000
    assert res.remaining_cents == 1000000
    assert res.required_fortnightly_cents is not None
    assert res.projected_completion_date is not None


def test_recurring_detection_and_scenario_comparison() -> None:
    rows = [
        (date(2026, 9, 4), -799, "SPOTIFY", "Subscription services", False),
        (date(2026, 10, 4), -799, "SPOTIFY", "Subscription services", False),
        (date(2026, 11, 4), -799, "SPOTIFY", "Subscription services", False),
        # Irregular PayID transfers with varying amounts / non-commitment category should be ignored
        (date(2026, 9, 30), -2000, "R RAJEEV", "Uncategorised", False),
        (date(2026, 10, 19), -1100, "R RAJEEV", "Uncategorised", False),
        (date(2026, 11, 8), -1500, "R RAJEEV", "Uncategorised", False),
    ]
    rec = detect_recurring_payments(rows)
    assert len(rec) == 1
    assert rec[0].merchant == "SPOTIFY"
    assert rec[0].estimated_cadence == "Monthly"

    comp = compare_scenarios(100000, 400000, 300000, 50000, extra_monthly_savings_cents=20000)
    assert comp.five_year_difference_cents == 20000 * 60


def test_suggest_recurring_groups_spotify_with_reference_ids() -> None:
    rows = [
        (date(2026, 10, 6), -799, "SPOTIFY P478C1BDD1 SYDNEY", "Subscription services", False),
        (date(2026, 11, 4), -799, "SPOTIFY P48BA8C1F5 SYDNEY", "Subscription services", False),
    ]
    sugg = suggest_recurring_candidates(rows, already_saved_merchants=set())
    assert len(sugg) == 1
    assert sugg[0].merchant == "SPOTIFY"
    assert sugg[0].estimated_cadence == "Monthly"
    assert sugg[0].avg_amount_cents == 799


def test_wealth_portfolio_and_super_projection() -> None:
    portfolio = evaluate_portfolio([HoldingSpec(1, "VAS", "Vanguard Australian Shares", "ETF", 10000, 9000, 10000)])
    assert portfolio.total_cost_cents == 90000
    assert portfolio.total_value_cents == 100000
    assert portfolio.total_gain_loss_cents == 10000

    proj = project_superannuation(1000000, 698316, 0, 700, horizons=(5, 10))
    assert len(proj) == 2
    assert proj[1].projected_balance_cents > proj[0].projected_balance_cents


def test_phases_3_to_6_api_endpoints(tmp_path) -> None:
    db_file = tmp_path / "test_p3_6.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    with TestingSession() as db:
        seed_defaults(db)

    def override_get_db():
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)

        cats = client.get("/api/categories").json()
        groceries_id = next(c["id"] for c in cats if c["name"] == "Groceries")

        b_res = client.post(
            "/api/budgets",
            json={"category_id": groceries_id, "period": "monthly", "limit_cents": 40000, "name": "Weekly Food"},
        )
        assert b_res.status_code == 201
        assert b_res.json()["name"] == "Weekly Food"

        b_id = b_res.json()["budget_id"]
        b_patch = client.patch(
            f"/api/budgets/{b_id}",
            json={"name": "Coles & Aldi"},
        )
        assert b_patch.status_code == 200
        assert b_patch.json()["name"] == "Coles & Aldi"

        # Allow creating a second budget in the same category with a different name
        b2_res = client.post(
            "/api/budgets",
            json={"category_id": groceries_id, "period": "fortnightly", "limit_cents": 15000, "name": "Snacks & Lunches"},
        )
        assert b2_res.status_code == 201
        assert b2_res.json()["name"] == "Snacks & Lunches"
        all_budgets = client.get("/api/budgets").json()
        assert len(all_budgets) == 2

        # Import Groceries spend in Oct 2026 ($150) and Nov 2026 ($450) and verify ?month=YYYY-MM
        smart_id = client.get("/api/accounts").json()[0]["id"]
        csv_two_months = (
            b'15/10/2026,"-150.00","COLES SUPERMARKET","2500.00"\n'
            b'15/11/2026,"-450.00","COLES SUPERMARKET","2050.00"\n'
        )
        client.post(
            "/api/imports/commbank",
            data={"account_id": str(smart_id)},
            files={"file": ("groceries.csv", csv_two_months, "text/csv")},
        )
        oct_budgets = client.get("/api/budgets?month=2026-10").json()
        assert len(oct_budgets) == 1
        assert oct_budgets[0]["spent_cents"] == 15000
        assert oct_budgets[0]["remaining_cents"] == 25000
        assert oct_budgets[0]["status"] == "ok"

        nov_budgets = client.get("/api/budgets?month=2026-11").json()
        assert len(nov_budgets) == 1
        assert nov_budgets[0]["spent_cents"] == 45000
        assert nov_budgets[0]["remaining_cents"] == -5000
        assert nov_budgets[0]["status"] == "over"

        assert client.get("/api/budgets?month=invalid").status_code == 400

        pc_res = client.get("/api/budgets/pay-cycle")
        assert pc_res.status_code == 200
        pc = pc_res.json()
        assert pc["income_basis"] == "salary"
        assert pc["declared_net_fortnightly_cents"] > 0
        assert pc["declared_net_monthly_cents"] > pc["declared_net_fortnightly_cents"]
        assert pc["budgeted_monthly_cents"] == 40000
        assert pc["budgeted_fortnightly_cents"] > 0

        # Persist custom fortnightly net pay and reset back
        np_res = client.put("/api/budgets/net-pay", json={"net_fortnightly_cents": 215000})
        assert np_res.status_code == 200
        assert np_res.json()["net_fortnightly_cents"] == 215000
        assert client.get("/api/budgets/pay-cycle").json()["net_fortnightly_cents"] == 215000
        reset_res = client.put("/api/budgets/net-pay", json={"net_fortnightly_cents": None})
        assert reset_res.status_code == 200
        assert reset_res.json()["income_basis"] == "salary"

        # Custom income basis check
        pc_custom = client.get("/api/budgets/pay-cycle?basis=custom&custom_fortnightly_cents=200000").json()
        assert pc_custom["income_basis"] == "custom"
        assert pc_custom["net_fortnightly_cents"] == 200000

        goals = client.get("/api/goals").json()
        assert len(goals) >= 4
        c_res = client.post(f"/api/goals/{goals[0]['goal_id']}/contribute", json={"amount_cents": 50000})
        assert c_res.status_code == 200
        assert c_res.json()["current_cents"] == 50000

        # Update goal name, target, and fortnightly contribution
        u_res = client.patch(
            f"/api/goals/{goals[0]['goal_id']}",
            json={"name": "Mazda 3 Hatch", "target_cents": 1500000, "planned_contribution_cents": 35000},
        )
        assert u_res.status_code == 200
        assert u_res.json()["name"] == "Mazda 3 Hatch"
        assert u_res.json()["target_cents"] == 1500000
        assert u_res.json()["planned_contribution_cents"] == 35000

        assert client.get("/api/insights").status_code == 200
        rec_res = client.post(
            "/api/insights/recurring",
            json={"merchant": "Fauzi Rent", "category_name": "Rent", "amount_cents": 78000, "cadence": "Monthly"},
        )
        assert rec_res.status_code == 201
        rec_id = rec_res.json()["id"]
        assert len(client.get("/api/insights").json()["recurring"]) == 1
        assert client.delete(f"/api/insights/recurring/{rec_id}").status_code == 204
        assert len(client.get("/api/insights").json()["recurring"]) == 0
        assert client.post("/api/insights/scenario", json={"extra_monthly_savings_cents": 20000}).status_code == 200

        h_res = client.post(
            "/api/wealth/holdings",
            json={"symbol": "VAS", "name": "Vanguard Aus", "asset_type": "ETF", "units": "5", "avg_cost_cents": 9000, "current_price_cents": 9500},
        )
        assert h_res.status_code == 201
        w_res = client.get("/api/wealth")
        assert w_res.status_code == 200
        assert w_res.json()["investments_value_cents"] == 47500
    finally:
        app.dependency_overrides.clear()


def test_fauzi_rent_vs_bills_and_auto_split(tmp_path) -> None:
    db_file = tmp_path / "test_fauzi.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    with TestingSession() as db:
        seed_defaults(db)

    def override_get_db():
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        accts = client.get("/api/accounts").json()
        smart_id = accts[0]["id"]
        cats = client.get("/api/categories").json()
        rent_id = next(c["id"] for c in cats if c["name"] == "Rent")

        # Import 3 Fauzi transactions:
        # 1. $50 bill payment (small amount)
        # 2. $650 standard rent
        # 3. $710 combined rent ($650) + bill ($60)
        csv_bytes = (
            b'10/11/2026,"-50.00","Transfer To Fauzi PayID","2000.00"\n'
            b'12/11/2026,"-650.00","Transfer To Fauzi PayID","1350.00"\n'
            b'15/11/2026,"-710.00","Transfer To Fauzi PayID","640.00"\n'
        )
        imp = client.post(
            "/api/imports/commbank",
            data={"account_id": str(smart_id)},
            files={"file": ("fauzi.csv", csv_bytes, "text/csv")},
        )
        assert imp.status_code == 200

        # User categorises Fauzi as Rent with apply_to_merchant=True
        txs = client.get("/api/transactions").json()
        rent_tx = next(t for t in txs if t["amount_cents"] == -65000)
        client.patch(
            f"/api/transactions/{rent_tx['id']}",
            json={"category_id": rent_id, "apply_to_merchant": True},
        )

        # User adds fixed recurring Rent ($650) for Fauzi
        client.post(
            "/api/insights/recurring",
            json={"merchant": "Fauzi", "category_name": "Rent", "amount_cents": 65000, "cadence": "Monthly"},
        )

        # Verify:
        # - $50 payment is automatically in Utilities (NOT Rent)
        # - $650 payment is in Rent
        # - $710 combined payment was auto-split into -$650 Rent and -$60 Utilities
        after_txs = client.get("/api/transactions").json()
        fifty_tx = next(t for t in after_txs if t["amount_cents"] == -5000)
        assert fifty_tx["category_name"] == "Utilities"

        rent_rows = [t for t in after_txs if t["category_name"] == "Rent"]
        assert len(rent_rows) == 2
        assert all(t["amount_cents"] == -65000 for t in rent_rows)

        sixty_split = next(t for t in after_txs if t["amount_cents"] == -6000)
        assert sixty_split["category_name"] == "Utilities"
        assert "[Split:" in sixty_split["description_raw"]

        # Test manual unsplit (merge back)
        unsplit_res = client.post(f"/api/transactions/{sixty_split['id']}/unsplit")
        assert unsplit_res.status_code == 200
        assert unsplit_res.json()["amount_cents"] == -71000
    finally:
        app.dependency_overrides.clear()
