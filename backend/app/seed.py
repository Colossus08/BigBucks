from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal, init_db
from app.engine.money import to_cents
from app.models.finance import (
    Account,
    Category,
    FinancialGoal,
    IncomeProfile,
    Institution,
    MerchantRule,
    SuperAccount,
)

DEFAULT_CATEGORIES: list[tuple[str, str, bool, bool]] = [
    # Essential expenses (§7.2)
    ("Rent", "Essential", False, False),
    ("Utilities", "Essential", False, False),
    ("Internet", "Essential", False, False),
    ("Phone", "Essential", False, False),
    ("Insurance", "Essential", False, False),
    ("Groceries", "Essential", False, False),
    ("Medical expenses", "Essential", False, False),
    # Transport (§7.2)
    ("Public transport", "Transport", False, False),
    ("Fuel", "Transport", False, False),
    ("Parking", "Transport", False, False),
    ("Vehicle maintenance", "Transport", False, False),
    ("Rideshare", "Transport", False, False),
    # Lifestyle (§7.2)
    ("Restaurants", "Lifestyle", False, False),
    ("Cafes", "Lifestyle", False, False),
    ("Entertainment", "Lifestyle", False, False),
    ("Shopping", "Lifestyle", False, False),
    ("Hobbies", "Lifestyle", False, False),
    ("Travel", "Lifestyle", False, False),
    # Financial commitments (§7.2)
    ("Loan repayments", "Commitments", False, False),
    ("Credit card repayments", "Commitments", False, False),
    ("Subscription services", "Commitments", False, False),
    ("Other recurring payments", "Commitments", False, False),
    # Financial growth (§7.2)
    ("Savings transfers", "Growth", False, False),
    ("Investment contributions", "Growth", False, False),
    ("Superannuation contributions", "Growth", False, False),
    # Giving
    ("Tithes & Offering", "Giving", False, False),
    # Income & system categories
    ("Salary", "Income", True, False),
    ("Allowance / Gifts", "Income", True, False),
    ("Other income", "Income", True, False),
    ("Reimbursements", "Reimbursements", False, False),
    ("Internal transfer", "Transfer", False, True),
    ("Uncategorised", "Other", False, True),
]

DEFAULT_RULES: list[tuple[str, str, str, int]] = [
    # (pattern, match_type, category_name, priority)
    ("ACCESS4", "contains", "Salary", 50),
    ("POORAV PTY LTD", "contains", "Salary", 55),
    ("Transfer To Fauzi.*rent", "regex", "Rent", 60),
    ("Transfer To Fauzi.*bills", "regex", "Utilities", 60),
    ("SHILOH", "contains", "Tithes & Offering", 70),
    ("TITHE.LY", "contains", "Tithes & Offering", 70),
    # Groceries
    ("COLES", "contains", "Groceries", 100),
    ("WW METRO", "contains", "Groceries", 100),
    ("WOOLWORTHS", "contains", "Groceries", 100),
    ("ALDI", "contains", "Groceries", 100),
    ("MILKRUN", "contains", "Groceries", 100),
    ("IGA", "contains", "Groceries", 100),
    ("TREATS N NEEDS", "contains", "Groceries", 100),
    # Transport & Rideshare
    ("MYKI", "contains", "Public transport", 100),
    ("PTV", "contains", "Public transport", 100),
    ("UBER *TRIP", "contains", "Rideshare", 100),
    ("DIDI MOBILITY", "contains", "Rideshare", 100),
    ("7-ELEVEN", "contains", "Fuel", 100),
    ("BP ", "contains", "Fuel", 100),
    ("AMPOL", "contains", "Fuel", 100),
    ("SHELL", "contains", "Fuel", 100),
    # Medical & Phone
    ("CHEMIST WAREHOUSE", "contains", "Medical expenses", 100),
    ("CWH ", "contains", "Medical expenses", 100),
    ("PHARMACY", "contains", "Medical expenses", 100),
    ("LEBARA", "contains", "Phone", 100),
    ("OPTUS", "contains", "Phone", 100),
    ("TELSTRA", "contains", "Phone", 100),
    ("VODAFONE", "contains", "Phone", 100),
    # Restaurants & Takeaway
    ("UBER *EATS", "contains", "Restaurants", 95),
    ("DOORDASH", "contains", "Restaurants", 95),
    ("MENULOG", "contains", "Restaurants", 95),
    ("MCDONALDS", "contains", "Restaurants", 100),
    ("KFC", "contains", "Restaurants", 100),
    ("NANDOS", "contains", "Restaurants", 100),
    ("HUNGRY JACK", "contains", "Restaurants", 100),
    ("SUBWAY", "contains", "Restaurants", 100),
    ("DOMINO", "contains", "Restaurants", 100),
    ("GRILLD", "contains", "Restaurants", 100),
    ("GUZMAN", "contains", "Restaurants", 100),
    ("HOT STAR", "contains", "Restaurants", 100),
    ("DESSERT", "contains", "Restaurants", 100),
    ("TANTUNI", "contains", "Restaurants", 100),
    ("SUSHI", "contains", "Restaurants", 100),
    ("PIZZA", "contains", "Restaurants", 100),
    ("BURGER", "contains", "Restaurants", 100),
    ("KEBAB", "contains", "Restaurants", 100),
    ("RAMEN", "contains", "Restaurants", 100),
    ("BISTRO", "contains", "Restaurants", 100),
    ("KITCHEN", "contains", "Restaurants", 100),
    ("RESTAURANT", "contains", "Restaurants", 100),
    # Cafes & Coffee
    ("BAKERY", "contains", "Cafes", 100),
    ("CAFE", "contains", "Cafes", 100),
    ("COFFEE", "contains", "Cafes", 100),
    ("ESPRESSO", "contains", "Cafes", 100),
    # Entertainment, Shopping, Subscriptions, Travel
    ("STEAMGAMES", "contains", "Entertainment", 100),
    ("STEAM PURCHASE", "contains", "Entertainment", 100),
    ("HOYTS", "contains", "Entertainment", 100),
    ("VILLAGE CINEMA", "contains", "Entertainment", 100),
    ("SAVERS AUSTRALIA", "contains", "Shopping", 100),
    ("KMART", "contains", "Shopping", 100),
    ("TARGET", "contains", "Shopping", 100),
    ("BUNNINGS", "contains", "Shopping", 100),
    ("JB HI-FI", "contains", "Shopping", 100),
    ("UNIQLO", "contains", "Shopping", 100),
    ("COTTON ON", "contains", "Shopping", 100),
    ("AMAZON", "contains", "Shopping", 100),
    ("JETSTAR", "contains", "Travel", 100),
    ("QANTAS", "contains", "Travel", 100),
    ("SPOTIFY", "contains", "Subscription services", 100),
    ("NETFLIX", "contains", "Subscription services", 100),
    ("GOOGLE ONE", "contains", "Subscription services", 100),
    ("APPLE.COM", "contains", "Subscription services", 100),
    ("SHILOH", "contains", "Tithes & Offering", 80),
    ("TITHE.LY", "contains", "Tithes & Offering", 80),
]


def seed_defaults(db: Session) -> None:
    """Idempotently seed CommBank, Smart Access, categories, rules, and income profile."""
    commbank = db.scalar(select(Institution).where(Institution.code == "commbank"))
    if commbank is None:
        commbank = Institution(name="Commonwealth Bank of Australia", code="commbank")
        db.add(commbank)
        db.flush()

    smart_access = db.scalar(
        select(Account).where(Account.institution_id == commbank.id, Account.name == "Smart Access")
    )
    if smart_access is None:
        db.add(
            Account(
                institution_id=commbank.id,
                name="Smart Access",
                account_number_mask="xx0374",
                type="transaction",
                is_own=True,
                current_balance_cents=0,
            )
        )

    existing_cats = {c.name: c for c in db.scalars(select(Category)).all()}
    for name, group, is_income, is_system in DEFAULT_CATEGORIES:
        if name not in existing_cats:
            cat = Category(name=name, group=group, is_income=is_income, is_system=is_system)
            db.add(cat)
            db.flush()
            existing_cats[name] = cat

    existing_patterns = {
        (r.pattern.upper(), r.source) for r in db.scalars(select(MerchantRule)).all()
    }
    for pattern, match_type, cat_name, priority in DEFAULT_RULES:
        if (pattern.upper(), "seed") not in existing_patterns and cat_name in existing_cats:
            db.add(
                MerchantRule(
                    pattern=pattern,
                    match_type=match_type,
                    category_id=existing_cats[cat_name].id,
                    priority=priority,
                    source="seed",
                    is_active=True,
                )
            )

    profile = db.scalar(select(IncomeProfile))
    if profile is None:
        db.add(
            IncomeProfile(
                employer_name="Access4",
                gross_annual_cents=to_cents(settings.gross_annual_salary),
                pay_frequency=settings.pay_frequency,
                super_rate_bps=int(settings.super_rate * 10000),
            )
        )

    if db.scalar(select(FinancialGoal)) is None:
        db.add_all(
            [
                FinancialGoal(
                    name="Emergency Fund",
                    category="emergency",
                    target_cents=1000000,
                    extra_costs_cents=0,
                    current_cents=0,
                    priority=1,
                    planned_contribution_cents=15000,
                    contribution_frequency="fortnightly",
                ),
                FinancialGoal(
                    name="Car Purchase",
                    category="car",
                    target_cents=1500000,
                    extra_costs_cents=250000,
                    current_cents=0,
                    priority=2,
                    planned_contribution_cents=20000,
                    contribution_frequency="fortnightly",
                ),
                FinancialGoal(
                    name="Wedding",
                    category="wedding",
                    target_cents=2000000,
                    extra_costs_cents=0,
                    current_cents=0,
                    priority=3,
                    planned_contribution_cents=15000,
                    contribution_frequency="fortnightly",
                ),
                FinancialGoal(
                    name="Honeymoon",
                    category="honeymoon",
                    target_cents=600000,
                    extra_costs_cents=0,
                    current_cents=0,
                    priority=4,
                    planned_contribution_cents=7500,
                    contribution_frequency="fortnightly",
                ),
            ]
        )

    if db.scalar(select(SuperAccount)) is None:
        db.add(
            SuperAccount(
                fund_name="MySuper Account",
                balance_cents=0,
                personal_monthly_cents=0,
                expected_return_bps=700,
            )
        )

    db.commit()


if __name__ == "__main__":
    init_db()
    with SessionLocal() as session:
        seed_defaults(session)
    print("Database seeded successfully.")
