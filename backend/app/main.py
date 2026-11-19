from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    accounts,
    auth,
    budgets,
    categories,
    exports,
    goals,
    imports,
    income,
    insights,
    rules,
    summary,
    transactions,
    wealth,
)
from app.auth import require_auth
from app.config import settings
from app.db import SessionLocal, init_db
from app.seed import seed_defaults


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with SessionLocal() as db:
        seed_defaults(db)
    yield


app = FastAPI(
    title="Personal Finance Manager API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_auth_dep = [Depends(require_auth)]

app.include_router(auth.router)
app.include_router(accounts.router, dependencies=_auth_dep)
app.include_router(categories.router, dependencies=_auth_dep)
app.include_router(imports.router, dependencies=_auth_dep)
app.include_router(transactions.router, dependencies=_auth_dep)
app.include_router(summary.router, dependencies=_auth_dep)
app.include_router(income.router, dependencies=_auth_dep)
app.include_router(rules.router, dependencies=_auth_dep)
app.include_router(budgets.router, dependencies=_auth_dep)
app.include_router(goals.router, dependencies=_auth_dep)
app.include_router(insights.router, dependencies=_auth_dep)
app.include_router(wealth.router, dependencies=_auth_dep)
app.include_router(exports.router, dependencies=_auth_dep)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
