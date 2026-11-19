from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app.seed import seed_defaults


def test_full_import_dedupe_summary_and_recategorise(tmp_path) -> None:
    db_file = tmp_path / "test.db"
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

        accounts = client.get("/api/accounts").json()
        assert len(accounts) == 1
        smart_access_id = accounts[0]["id"]

        csv_body = (
            '16/11/2026,"-50.00","COLES 0537 POINT COOK AU","+150.00"\n'
            '15/11/2026,"-80.00","Transfer to xx0464 CommBank app","+200.00"\n'
            '14/11/2026,"+2000.00","ACCESS4 PTY LTD SALARY","+280.00"\n'
            '13/11/2026,"-25.00","MYSTERY SHOP MELBOURNE","-1720.00"\n'
        )
        r1 = client.post(
            "/api/imports/commbank",
            data={"account_id": str(smart_access_id)},
            files={"file": ("test.csv", csv_body, "text/csv")},
        )
        assert r1.status_code == 200
        report1 = r1.json()
        assert report1["inserted_rows"] == 4
        assert report1["duplicate_rows"] == 0

        # Re-importing the exact same CSV inserts 0 rows
        r2 = client.post(
            "/api/imports/commbank",
            data={"account_id": str(smart_access_id)},
            files={"file": ("test.csv", csv_body, "text/csv")},
        )
        assert r2.json()["inserted_rows"] == 0
        assert r2.json()["duplicate_rows"] == 4

        summary = client.get("/api/summary?period=month&date=2026-11-16").json()
        assert summary["income_cents"] == 200000
        assert summary["expenses_cents"] == 7500  # 50 + 25 (transfer excluded)

        # Recategorise mystery cafe to Restaurants
        txs = client.get("/api/transactions?q=MYSTERY").json()
        assert len(txs) == 1
        cats = client.get("/api/categories").json()
        restaurants_id = next(c["id"] for c in cats if c["name"] == "Restaurants")

        patch_res = client.patch(
            f"/api/transactions/{txs[0]['id']}",
            json={"category_id": restaurants_id, "apply_to_merchant": True},
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["transaction"]["category_name"] == "Restaurants"

        # Undo latest learned rule resets it back to Uncategorised
        undo_res = client.post("/api/rules/undo-latest")
        assert undo_res.status_code == 200
        assert undo_res.json()["updated_count"] == 1

        uncat_merchants = client.get("/api/transactions/merchants/uncategorised").json()
        assert any(m["merchant"] == "MYSTERY SHOP MELBOURNE" for m in uncat_merchants)

        # Bulk categorise restores it
        bulk_res = client.post(
            "/api/transactions/bulk-categorise",
            json={"merchants": ["MYSTERY SHOP MELBOURNE"], "category_id": restaurants_id},
        )
        assert bulk_res.status_code == 200
        assert bulk_res.json()["updated_count"] == 1
    finally:
        app.dependency_overrides.clear()
