"""SEC-02: authenticated POST /api/wallet/topup must not credit or write a topup transaction.

The wallet route is imported inside the test so collecting this file does not open a database client.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient


class _Users:
    def __init__(self):
        self.updates = []

    async def update_one(self, query, update):
        self.updates.append((query, update))


class _Transactions:
    def __init__(self):
        self.docs = []

    async def insert_one(self, doc):
        self.docs.append(doc)


class _DB:
    def __init__(self):
        self.users = _Users()
        self.transactions = _Transactions()


def test_authenticated_direct_topup_does_not_mutate_wallet(monkeypatch):
    import routes.wallet as wallet

    fake = _DB()
    monkeypatch.setattr(wallet, "db", fake)
    app = FastAPI()
    app.include_router(wallet.router)
    app.dependency_overrides[wallet.get_current_user] = lambda: {
        "id": "sec02-user",
        "email": "sec02@example.com",
        "role": "client",
    }
    response = TestClient(app).post("/api/wallet/topup", params={"amount": 100})
    assert response.status_code == 403
    assert fake.users.updates == []
    assert fake.transactions.docs == []
