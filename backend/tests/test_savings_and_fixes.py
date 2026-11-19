from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.engine.budgeting import BudgetSpec, evaluate_budgets
from app.engine.savings import (
    net_moved_by_mask,
    parse_transfer_mask,
    suggest_transfer_counterparties,
)
from app.engine.summary import TransactionRecord, summarise
from app.importers.commbank_csv import parse_commbank_csv
from app.main import app
from app.migrate import run_migrations
from app.models.finance import Category, MerchantRule
from app.seed import seed_defaults
from app.services.categoriser import categorise_transaction


# ---------- pure engine tests ----------


def test_refund_reduces_category_and_unclassified_money_is_not_income() -> None:
    records = [
        TransactionRecord(date(2026, 11, 1), 200000, 1, "Salary", "Income", False),
        TransactionRecord(date(2026, 11, 2), -849, 2, "Subscription services", "Commitments", False),
        TransactionRecord(date(2026, 11, 3), 685, 2, "Subscription services", "Commitments", False),  # refund
        TransactionRecord(date(2026, 11, 4), 15000, None, "Uncategorised", "Other", False),  # cash deposit
        TransactionRecord(date(2026, 11, 5), 800, 3, "Other income", "Income", False),
    ]
    res = summarise(records, date(2026, 11, 1), date(2026, 11, 30))
    assert res.income_cents == 200800  # salary + categorised other income only
    assert res.refunds_cents == 685
    assert res.gross_expenses_cents == 164
    assert res.expenses_cents == 164
    assert res.unclassified_in_cents == 15000
    assert res.by_group == {"Commitments": 164}
    assert res.net_savings_cents == 200800 - 164


def test_refund_larger_than_spend_never_goes_negative() -> None:
    records = [
        TransactionRecord(date(2026, 11, 2), -500, 2, "Shopping", "Lifestyle", False),
        TransactionRecord(date(2026, 11, 3), 900, 2, "Shopping", "Lifestyle", False),
    ]
    res = summarise(records, date(2026, 11, 1), date(2026, 11, 30))
    assert res.expenses_cents == 0
    assert res.by_category == []


def test_budget_spend_is_net_of_refunds() -> None:
    specs = [BudgetSpec(1, 10, "Shopping", "Lifestyle", "monthly", 50000)]
    records = [
        TransactionRecord(date(2026, 11, 2), -20000, 10, "Shopping", "Lifestyle", False),
        TransactionRecord(date(2026, 11, 3), 5000, 10, "Shopping", "Lifestyle", False),
    ]
    assert evaluate_budgets(specs, records, date(2026, 11, 15))[0].spent_cents == 15000


def test_transfer_parsing_and_net_moved() -> None:
    assert parse_transfer_mask("Transfer to xx0464 CommBank app") == "xx0464"
    assert parse_transfer_mask("Transfer from XX3834 CommBank app") == "xx3834"
    assert parse_transfer_mask("Transfer To R RAJEEV PayID Phone from CommBank App") is None
    assert parse_transfer_mask("COLES 0537 POINT COOK AU") is None

    rows = [
        (date(2026, 11, 1), -10000, "Transfer to xx0464 CommBank app"),
        (date(2026, 11, 2), 2000, "Transfer from xx0464 CommBank app"),
        (date(2026, 10, 1), -5000, "Transfer to xx0464 CommBank app"),
        (date(2026, 11, 3), -3000, "Transfer to xx1800 CommBank app"),
    ]
    assert net_moved_by_mask(rows) == {"xx0464": 13000, "xx1800": 3000}
    assert net_moved_by_mask(rows, start=date(2026, 11, 1), end=date(2026, 11, 30)) == {
        "xx0464": 8000,
        "xx1800": 3000,
    }
    sugg = suggest_transfer_counterparties(rows, tracked_masks={"XX0464"})
    assert [s.mask for s in sugg] == ["xx1800"]
    assert sugg[0].count == 1 and sugg[0].net_moved_in_cents == 3000


def test_short_keyword_uses_whole_word_matching() -> None:
    groceries = Category(id=1, name="Groceries", group="Essential", is_income=False, is_system=False)
    uncat = Category(id=2, name="Uncategorised", group="Other", is_income=False, is_system=True)
    cats = {1: groceries, 2: uncat}
    rules = [
        MerchantRule(id=1, pattern="IGA", match_type="contains", category_id=1, priority=100, source="seed", is_active=True)
    ]

    # Should NOT match "IGA" inside "GIGABYTE"
    r_false = categorise_transaction("GIGABYTE STORE", "GIGABYTE STORE", -5000, rules, None, 2, cats)
    assert r_false.category_id == 2

    # SHOULD match "IGA" as a standalone word
    r_true = categorise_transaction("IGA X-PRESS MELBOURNE", "IGA X-PRESS MELBOURNE", -2500, rules, None, 2, cats)
    assert r_true.category_id == 1


def test_running_balance_continuity_check() -> None:
    # Broken balance: 100.00 + (-10.00) should be 90.00, not 50.00
    bad_csv = (
        '16/11/2026,"-10.00","COLES 0537","+50.00"\n'
        '15/11/2026,"-20.00","MYKI","+100.00"\n'
    )
    parsed = parse_commbank_csv(bad_csv)
    assert len(parsed.balance_warnings) == 1
    assert "expected balance $90.00" in parsed.balance_warnings[0]


# ---------- API tests ----------


@pytest.fixture()
def client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'api.db'}", connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    with Session() as db:
        seed_defaults(db)

    def override():
        with Session() as db:
            yield db

    app.dependency_overrides[get_db] = override
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


CSV = (
    '16/11/2026,"-100.00","Transfer to xx0464 CommBank app","+900.00"\n'
    '15/11/2026,"+20.00","Transfer from xx0464 CommBank app","+1000.00"\n'
    '14/11/2026,"-50.00","Transfer to xx1800 CommBank app","+980.00"\n'
    '13/11/2026,"-8.49","Google One Barangaroo AU AUS Card xx0374 Value Date: 02/11/2026","+1030.00"\n'
    '12/11/2026,"+6.85","Return GOOGLE*GOOGLE ONE SYDNEY NS AUS Card xx0374 Value Date: 02/11/2026","+1038.49"\n'
    '11/11/2026,"+150.00","CASH DEPOSIT CBA ATM MELB CENTRAL C VIC 301403 AUS","+1031.64"\n'
)


def _import(client: TestClient) -> int:
    account_id = client.get("/api/accounts").json()[0]["id"]
    res = client.post(
        "/api/imports/commbank",
        data={"account_id": str(account_id)},
        files={"file": ("t.csv", CSV, "text/csv")},
    )
    assert res.status_code == 200 and res.json()["inserted_rows"] == 6
    return account_id


def test_summary_handles_refunds_and_unclassified_money(client: TestClient) -> None:
    _import(client)
    s = client.get("/api/summary?period=month&date=2026-11-16").json()
    assert s["income_cents"] == 0
    assert s["refunds_cents"] == 685
    assert s["expenses_cents"] == 164
    assert s["unclassified_in_cents"] == 15000


def test_transaction_count_and_no_silent_cap(client: TestClient) -> None:
    _import(client)
    assert client.get("/api/transactions/count").json() == {"count": 6}
    assert len(client.get("/api/transactions").json()) == 6
    assert len(client.get("/api/transactions?limit=2").json()) == 2


def test_savings_accounts_flow_end_to_end(client: TestClient) -> None:
    smart_access_id = _import(client)

    sugg = {s["mask"]: s for s in client.get("/api/accounts/transfer-suggestions").json()}
    assert set(sugg) == {"xx0464", "xx1800"}
    assert sugg["xx0464"]["count"] == 2 and sugg["xx0464"]["net_moved_cents"] == 8000

    bad = client.post("/api/accounts", json={"name": "X", "account_number_mask": "0464", "type": "savings"})
    assert bad.status_code == 400
    created = client.post(
        "/api/accounts",
        json={"name": "Holiday Saver", "account_number_mask": "XX0464", "type": "savings"},
    )
    assert created.status_code == 201
    saver_id = created.json()["id"]
    assert client.post(
        "/api/accounts",
        json={"name": "Again", "account_number_mask": "xx0464", "type": "savings"},
    ).status_code == 409

    assert client.get("/api/accounts/savings").json() == [
        {"id": saver_id, "name": "Holiday Saver", "net_moved_cents": 8000, "transfer_count": 2}
    ]
    assert [s["mask"] for s in client.get("/api/accounts/transfer-suggestions").json()] == ["xx1800"]

    # A goal linked to the account picks up the money moved into it automatically.
    bad_goal = client.post(
        "/api/goals",
        json={"name": "Nope", "target_cents": 100000, "linked_account_id": smart_access_id},
    )
    assert bad_goal.status_code == 400
    goal = client.post(
        "/api/goals",
        json={"name": "Trip", "target_cents": 100000, "linked_account_id": saver_id},
    ).json()
    assert goal["current_cents"] == 8000
    assert goal["linked_moved_cents"] == 8000
    assert goal["linked_account_name"] == "Holiday Saver"
    manual = client.post(f"/api/goals/{goal['goal_id']}/contribute", json={"amount_cents": 2000}).json()
    assert manual["current_cents"] == 10000  # manual + linked

    assert client.get("/api/summary?period=month&date=2026-11-16").json()["moved_to_savings_cents"] == 8000
    assert client.get("/api/insights").status_code == 200

    # Accounts with imported transactions can't be removed; tracked savings accounts can.
    assert client.delete(f"/api/accounts/{smart_access_id}").status_code == 400
    assert client.delete(f"/api/accounts/{saver_id}").status_code == 204
    trip = next(g for g in client.get("/api/goals").json() if g["name"] == "Trip")
    assert trip["linked_account_id"] is None
    assert trip["current_cents"] == 2000  # only the manual part remains
    assert client.get("/api/summary?period=month&date=2026-11-16").json()["moved_to_savings_cents"] == 0


def test_categories_exclude_months_recurring_and_exports(client: TestClient) -> None:
    _import(client)

    # Available months endpoint
    months = client.get("/api/summary/months").json()
    assert months == ["2026-11"]

    # Create and delete custom category
    c_res = client.post("/api/categories", json={"name": "Pet Care", "group": "Essential"})
    assert c_res.status_code == 201
    cat_id = c_res.json()["id"]
    assert client.delete(f"/api/categories/{cat_id}").status_code == 204

    # Exclude a transaction from reports
    txs = client.get("/api/transactions").json()
    google_one = next(t for t in txs if "GOOGLE ONE" in t["merchant"] and t["amount_cents"] < 0)
    ex_res = client.patch(f"/api/transactions/{google_one['id']}", json={"excluded": True})
    assert ex_res.status_code == 200
    assert ex_res.json()["transaction"]["kind"] == "excluded"

    # Recurring bill reduces available_to_spend_cents and is included in pay-cycle plan
    client.post(
        "/api/insights/recurring",
        json={"merchant": "Rent", "category_name": "Rent", "amount_cents": 65000, "cadence": "Monthly"},
    )
    sum_after = client.get("/api/summary?period=month&date=2026-11-16").json()
    assert sum_after["upcoming_bills_cents"] > 0
    assert sum_after["available_to_spend_cents"] == max(
        0, sum_after["bank_balance_cents"] - sum_after["upcoming_bills_cents"]
    )
    pc = client.get("/api/budgets/pay-cycle").json()
    assert pc["recurring_bills_cents"] == sum_after["upcoming_bills_cents"]

    # CSV and SQLite backup exports
    csv_exp = client.get("/api/exports/transactions.csv")
    assert csv_exp.status_code == 200 and "description_raw" in csv_exp.text
    db_exp = client.get("/api/exports/backup.db")
    assert db_exp.status_code == 200 and db_exp.content.startswith(b"SQLite format 3")


# ---------- migration tests ----------


def _tables(url: str) -> set[str]:
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_migrations_build_a_fresh_database_and_are_repeatable(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'fresh.db'}"
    run_migrations(url)
    run_migrations(url)  # second run must be a no-op
    assert {"transaction", "budget", "financial_goal", "recurring_payment", "alembic_version"} <= _tables(url)
    engine = create_engine(url)
    try:
        cols = {c["name"] for c in inspect(engine).get_columns("financial_goal")}
    finally:
        engine.dispose()
    assert "linked_account_id" in cols


def test_migrations_upgrade_a_database_created_without_alembic(tmp_path) -> None:
    """Simulates a pre-0003 database: initial tables exist, no alembic_version, goal table lacks linked_account_id."""
    url = f"sqlite:///{tmp_path / 'legacy.db'}"
    engine = create_engine(url)
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE financial_goal"))
        conn.execute(
            text(
                "CREATE TABLE financial_goal ("
                "id INTEGER PRIMARY KEY, name VARCHAR(120) NOT NULL, category VARCHAR(40) NOT NULL, "
                "target_cents INTEGER NOT NULL, extra_costs_cents INTEGER NOT NULL, current_cents INTEGER NOT NULL, "
                "target_date DATE, priority INTEGER NOT NULL, planned_contribution_cents INTEGER NOT NULL, "
                "contribution_frequency VARCHAR(20) NOT NULL)"
            )
        )
    engine.dispose()

    run_migrations(url)

    engine = create_engine(url)
    try:
        cols = {c["name"] for c in inspect(engine).get_columns("financial_goal")}
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    finally:
        engine.dispose()
    assert "linked_account_id" in cols
    assert version == "0004_roadmap_refinements"


def test_roadmap_features_safe_to_spend_price_hike_pairing_wfh_and_reconciliation(client: TestClient) -> None:
    _import(client)

    # 4.1 Safe-to-Spend & Daily Burn Rate exposed on summary
    s = client.get("/api/summary?period=month&date=2026-11-16").json()
    assert "safe_to_spend_cents" in s
    assert "daily_burn_rate_cents" in s
    assert s["days_until_payday"] >= 1

    # 4.2 Price-Creep & Hike Alert when charge exceeds recurring baseline
    rec = client.post(
        "/api/insights/recurring",
        json={"merchant": "GOOGLE ONE", "category_name": "Subscription services", "amount_cents": 500, "cadence": "Monthly"},
    ).json()
    ins = client.get("/api/insights").json()
    assert len(ins["price_hike_alerts"]) == 1
    alert = ins["price_hike_alerts"][0]
    assert alert["previous_cents"] == 500 and alert["new_cents"] == 849
    # Update baseline clears the alert
    assert client.patch(f"/api/insights/recurring/{rec['id']}?amount_cents=849").status_code == 200
    assert len(client.get("/api/insights").json()["price_hike_alerts"]) == 0

    # 4.3 Automated Internal Transfer Pairing across two owned accounts
    saver = client.post(
        "/api/accounts",
        json={"name": "NetBank Saver", "account_number_mask": "xx0464", "type": "savings"},
    ).json()
    saver_csv = '16/11/2026,"+100.00","Transfer from Smart Access","+500.00"\n'
    client.post(
        "/api/imports/commbank",
        data={"account_id": str(saver["id"])},
        files={"file": ("saver.csv", saver_csv, "text/csv")},
    )
    saver_txs = client.get(f"/api/transactions?account={saver['id']}").json()
    assert len(saver_txs) == 1
    assert saver_txs[0]["is_transfer"] is True
    assert saver_txs[0]["paired_transaction_id"] is not None

    # 4.4 ATO Tax Deduction & WFH Ledger + EOFY CSV export
    txs = client.get("/api/transactions").json()
    target_tx = next(t for t in txs if t["amount_cents"] < 0 and not t["is_transfer"])
    tag_res = client.patch(
        f"/api/transactions/{target_tx['id']}",
        json={"is_tax_deductible": True, "deduction_category": "D5", "receipt_ref": "INV-001"},
    )
    assert tag_res.status_code == 200 and tag_res.json()["transaction"]["is_tax_deductible"] is True

    wfh = client.post("/api/income/wfh", json={"work_date": "2026-11-16", "hours": 8.0, "note": "Remote dev"}).json()
    tax_dash = client.get("/api/income/tax-deductions?fy=2026-27").json()
    assert tax_dash["wfh_hours_total"] == 8.0
    assert tax_dash["wfh_deduction_cents"] == 536  # 8 * 67c
    assert tax_dash["expense_deduction_cents"] == abs(target_tx["amount_cents"])
    assert client.delete(f"/api/income/wfh/{wfh['id']}").status_code == 204
    assert client.get("/api/exports/tax-deductions.csv?fy=2026-27").status_code == 200

    # 3.1 Salary Reconciliation & 3.4 Holding Valuation Refresh
    recon = client.get("/api/income/reconciliation").json()
    assert recon["expected_net_period_cents"] > 0

    h = client.post(
        "/api/wealth/holdings",
        json={"symbol": "VGS", "name": "Vanguard Intl", "asset_type": "ETF", "units": "10", "avg_cost_cents": 10000, "current_price_cents": 11000},
    ).json()
    refreshed = client.patch(
        f"/api/wealth/holdings/{h['holding_id']}",
        json={"current_price_cents": 12500},
    ).json()
    assert refreshed["market_value_cents"] == 125000
