from datetime import date, datetime, timezone
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Institution(Base):
    """Financial institution (e.g. CommBank)."""

    __tablename__ = "institution"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)

    accounts: Mapped[list["Account"]] = relationship(back_populates="institution")


class Account(Base):
    """Bank account belonging to the user."""

    __tablename__ = "account"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institution.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    account_number_mask: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    type: Mapped[str] = mapped_column(String(30), nullable=False, default="transaction")
    is_own: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    current_balance_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    institution: Mapped["Institution"] = relationship(back_populates="accounts")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="account")


class Category(Base):
    """Transaction category and group hierarchy."""

    __tablename__ = "category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    group: Mapped[str] = mapped_column(String(40), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("category.id"), nullable=True)
    is_income: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (UniqueConstraint("name", "group", name="uq_category_name_group"),)


class MerchantRule(Base):
    """Rule mapping a merchant or description pattern to a category."""

    __tablename__ = "merchant_rule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pattern: Mapped[str] = mapped_column(String(200), nullable=False)
    match_type: Mapped[str] = mapped_column(String(20), nullable=False, default="contains")
    category_id: Mapped[int] = mapped_column(ForeignKey("category.id"), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="seed")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ImportBatch(Base):
    """Audit record for a CSV import."""

    __tablename__ = "import_batch"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    inserted_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Transaction(Base):
    """Financial transaction."""

    __tablename__ = "transaction"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"), nullable=False, index=True)
    import_batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batch.id"), nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    description_raw: Mapped[str] = mapped_column(String(500), nullable=False)
    merchant: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    balance_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("category.id"), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="actual")
    is_transfer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    paired_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transaction.id"), nullable=True)
    is_tax_deductible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deduction_category: Mapped[str | None] = mapped_column(String(20), nullable=True)
    receipt_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    dedupe_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    category_source: Mapped[str] = mapped_column(String(20), nullable=False, default="default")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)

    account: Mapped["Account"] = relationship(back_populates="transactions")
    category: Mapped["Category | None"] = relationship()


class IncomeProfile(Base):
    """Configured salary and super profile (seeded via app/seed.py or .env)."""

    __tablename__ = "income_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    gross_annual_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    pay_frequency: Mapped[str] = mapped_column(String(20), nullable=False, default="fortnightly")
    super_rate_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=1200)
    custom_net_fortnightly_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Budget(Base):
    """Category spending budget with multi-period support."""

    __tablename__ = "budget"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("category.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    period: Mapped[str] = mapped_column(String(20), nullable=False, default="monthly")
    effective_month: Mapped[str] = mapped_column(String(7), nullable=False, default="")
    limit_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    category: Mapped["Category"] = relationship()


class FinancialGoal(Base):
    """Savings goal."""

    __tablename__ = "financial_goal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False, default="general")
    target_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    extra_costs_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    planned_contribution_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    contribution_frequency: Mapped[str] = mapped_column(String(20), nullable=False, default="fortnightly")
    linked_account_id: Mapped[int | None] = mapped_column(ForeignKey("account.id"), nullable=True)


class GoalContribution(Base):
    """Contribution towards a savings goal."""

    __tablename__ = "goal_contribution"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey("financial_goal.id"), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[str] = mapped_column(String(200), nullable=False, default="")


class InvestmentHolding(Base):
    """Tracked investment holding."""

    __tablename__ = "investment_holding"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(30), nullable=False, default="ETF")
    units_milli: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_cost_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    current_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)


class SuperAccount(Base):
    """Superannuation balance and contribution settings."""

    __tablename__ = "super_account"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fund_name: Mapped[str] = mapped_column(String(120), nullable=False, default="Super Fund")
    balance_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    personal_monthly_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expected_return_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=700)


class RecurringPayment(Base):
    """User-confirmed recurring payment commitment."""

    __tablename__ = "recurring_payment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    merchant: Mapped[str] = mapped_column(String(200), nullable=False)
    merchant_pattern: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    category_id: Mapped[int | None] = mapped_column(ForeignKey("category.id"), nullable=True)
    category_name: Mapped[str] = mapped_column(String(80), nullable=False, default="Other recurring payments")
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    last_charged_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expected_day_of_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    cadence: Mapped[str] = mapped_column(String(20), nullable=False, default="Monthly")


class WfhLog(Base):
    """Work-from-home hours log for ATO fixed-rate deduction calculation (§4.4)."""

    __tablename__ = "wfh_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    work_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    hours: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    note: Mapped[str] = mapped_column(String(200), nullable=False, default="")
