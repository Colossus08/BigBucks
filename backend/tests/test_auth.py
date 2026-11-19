import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db import Base, get_db
from app.main import app
from app.seed import seed_defaults


def test_auth_flow(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_file = tmp_path / "auth_test.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    with TestingSession() as db:
        seed_defaults(db)

    def override_get_db():
        with TestingSession() as db:
            yield db

    monkeypatch.setattr(settings, "auth_username", "skydrop08")
    monkeypatch.setattr(settings, "auth_password", "2Peter1:4!")
    monkeypatch.setattr(settings, "auth_secret", "test-secret")
    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)

        # Unauthenticated status check
        st = client.get("/api/auth/status")
        assert st.status_code == 200
        assert st.json() == {"auth_required": True, "authenticated": False, "username": None}

        # Protected route rejects missing token
        assert client.get("/api/accounts").status_code == 401

        # Wrong password rejected
        bad = client.post("/api/auth/login", json={"username": "skydrop08", "password": "wrong"})
        assert bad.status_code == 401

        # Correct credentials succeed
        ok = client.post("/api/auth/login", json={"username": "skydrop08", "password": "2Peter1:4!"})
        assert ok.status_code == 200
        token = ok.json()["access_token"]

        # Authenticated status check
        st_ok = client.get("/api/auth/status", headers={"Authorization": f"Bearer {token}"})
        assert st_ok.status_code == 200
        assert st_ok.json()["authenticated"] is True
        assert st_ok.json()["username"] == "skydrop08"

        # Protected route succeeds with Bearer token
        assert client.get("/api/accounts", headers={"Authorization": f"Bearer {token}"}).status_code == 200

        # Query-param token works for file download links
        assert client.get(f"/api/exports/transactions.csv?token={token}").status_code == 200
    finally:
        app.dependency_overrides.clear()
