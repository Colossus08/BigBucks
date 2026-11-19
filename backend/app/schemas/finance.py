from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    institution_id: int
    name: str
    account_number_mask: str
    type: str
    is_own: bool
    current_balance_cents: int


class AccountCreate(BaseModel):
    name: str
    account_number_mask: str = ""
    type: str = "transaction"
    is_own: bool = True


class SavingsAccountOut(BaseModel):
    id: int
    name: str
    net_moved_cents: int
    transfer_count: int


class TransferSuggestionOut(BaseModel):
    mask: str
    count: int
    net_moved_cents: int


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    group: str
    parent_id: int | None
    is_income: bool
    is_system: bool


class CategoryCreate(BaseModel):
    name: str
    group: str = "Lifestyle"
    is_income: bool = False


class TransactionOut(BaseModel):
    id: int
    account_id: int
    date: date
    amount_cents: int
    description_raw: str
    merchant: str
    balance_cents: int | None
    category_id: int | None
    category_name: str
    category_group: str
    kind: str
    is_transfer: bool
    paired_transaction_id: int | None = None
    is_tax_deductible: bool = False
    deduction_category: str | None = None
    receipt_ref: str | None = None
    category_source: str


class TransactionUpdate(BaseModel):
    category_id: int | None = None
    apply_to_merchant: bool = False
    excluded: bool | None = None
    is_tax_deductible: bool | None = None
    deduction_category: str | None = None
    receipt_ref: str | None = None


class TransactionUpdateOut(BaseModel):
    transaction: TransactionOut
    updated_count: int


class TransactionSplitRequest(BaseModel):
    split_amount_cents: int
    category_id: int
    note: str = ""


class TransactionSplitOut(BaseModel):
    parent: TransactionOut
    child: TransactionOut


class UncategorisedMerchantOut(BaseModel):
    merchant: str
    count: int
    total_cents: int
    sample_description: str
    sample_transaction_id: int


class RuleCreate(BaseModel):
    pattern: str
    match_type: str = "contains"
    category_id: int


class RuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pattern: str
    match_type: str
    category_id: int
    category_name: str = ""
    priority: int
    source: str
    is_active: bool


class RuleApplyResult(BaseModel):
    updated_count: int


class BulkCategoriseRequest(BaseModel):
    merchants: list[str]
    category_id: int


class ImportErrorOut(BaseModel):
    row_number: int
    raw_line: str
    reason: str


class ImportReportOut(BaseModel):
    batch_id: int
    filename: str
    total_rows: int
    inserted_rows: int
    duplicate_rows: int
    error_rows: int
    errors: list[ImportErrorOut]
    balance_warnings: list[str] = []


class CategorySpendOut(BaseModel):
    category_id: int | None
    category_name: str
    category_group: str
    total_cents: int


class SummaryOut(BaseModel):
    period: str
    start_date: date
    end_date: date
    bank_balance_cents: int = 0
    upcoming_bills_cents: int = 0
    planned_goals_cents: int = 0
    safe_to_spend_cents: int = 0
    days_until_payday: int = 14
    daily_burn_rate_cents: int = 0
    available_to_spend_cents: int
    income_cents: int
    gross_expenses_cents: int
    refunds_cents: int
    reimbursements_cents: int
    unclassified_in_cents: int
    expenses_cents: int
    moved_to_savings_cents: int
    net_savings_cents: int
    savings_rate_pct: Decimal
    uncategorised_count: int
    by_group: dict[str, int]
    by_category: list[CategorySpendOut]


class MonthlyTrendPoint(BaseModel):
    month: str
    income_cents: int
    expenses_cents: int
    net_savings_cents: int


class IncomeEstimateOut(BaseModel):
    employer_name: str
    pay_frequency: str
    periods_per_year: int
    gross_annual: Decimal
    gross_period: Decimal
    income_tax_period: Decimal
    medicare_levy_period: Decimal
    total_tax_period: Decimal
    net_period: Decimal
    super_annual: Decimal
    super_period: Decimal
    tax_year: str


class BudgetCreate(BaseModel):
    category_id: int
    period: str = "monthly"
    limit_cents: int
    name: str = ""


class BudgetUpdate(BaseModel):
    name: str | None = None
    period: str | None = None
    limit_cents: int | None = None


class BudgetEvalOut(BaseModel):
    budget_id: int
    category_id: int
    category_name: str
    category_group: str
    period: str
    limit_cents: int
    spent_cents: int
    remaining_cents: int
    pct_used: Decimal
    projected_cents: int | None = None
    status: str
    name: str = ""


class BudgetRecommendationOut(BaseModel):
    category_id: int
    category_name: str
    category_group: str
    avg_monthly_cents: int
    recommended_monthly_cents: int
    reasoning: str


class CategoryHistoricalSpendOut(BaseModel):
    category_id: int
    category_name: str
    category_group: str
    avg_monthly_cents: int
    avg_fortnightly_cents: int
    current_month_cents: int


class PayCyclePlanOut(BaseModel):
    pay_frequency: str
    income_basis: str = "salary"
    net_period_cents: int
    budgeted_expenses_cents: int
    recurring_bills_cents: int = 0
    goal_contributions_cents: int
    unallocated_cents: int
    declared_net_fortnightly_cents: int = 0
    declared_net_monthly_cents: int = 0
    historical_income_fortnightly_cents: int = 0
    historical_income_monthly_cents: int = 0
    historical_expenses_fortnightly_cents: int = 0
    historical_expenses_monthly_cents: int = 0
    net_fortnightly_cents: int = 0
    net_monthly_cents: int = 0
    budgeted_fortnightly_cents: int = 0
    budgeted_monthly_cents: int = 0
    recurring_bills_fortnightly_cents: int = 0
    recurring_bills_monthly_cents: int = 0
    goal_contributions_fortnightly_cents: int = 0
    goal_contributions_monthly_cents: int = 0
    unallocated_fortnightly_cents: int = 0
    unallocated_monthly_cents: int = 0
    category_averages: list[CategoryHistoricalSpendOut] = []


class NetPayUpdate(BaseModel):
    net_fortnightly_cents: int | None = None


class GoalCreate(BaseModel):
    name: str
    category: str = "general"
    target_cents: int
    extra_costs_cents: int = 0
    current_cents: int = 0
    target_date: date | None = None
    priority: int = 1
    planned_contribution_cents: int = 0
    contribution_frequency: str = "fortnightly"
    linked_account_id: int | None = None


class GoalContribute(BaseModel):
    amount_cents: int
    note: str = ""


class GoalUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    target_cents: int | None = None
    planned_contribution_cents: int | None = None
    linked_account_id: int | None = None
    clear_linked_account: bool = False


class IncomeProfileUpdate(BaseModel):
    employer_name: str
    gross_annual_cents: int
    pay_frequency: str = "fortnightly"
    super_rate_bps: int = 1200


class GoalOut(BaseModel):
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
    linked_account_id: int | None = None
    linked_account_name: str | None = None
    linked_moved_cents: int = 0
    required_weekly_cents: int | None
    required_fortnightly_cents: int | None
    required_monthly_cents: int | None
    projected_completion_date: date | None


class RecurringItemOut(BaseModel):
    merchant: str
    category_name: str
    occurrences: int
    avg_amount_cents: int
    estimated_cadence: str
    estimated_monthly_cents: int
    last_date: date


class RecurringCreate(BaseModel):
    merchant: str
    category_name: str = "Other recurring payments"
    amount_cents: int
    cadence: str = "Monthly"


class RecurringDismiss(BaseModel):
    merchant: str
    category_name: str = "Other recurring payments"


class RecurringSavedOut(BaseModel):
    id: int
    merchant: str
    category_name: str
    amount_cents: int
    cadence: str
    estimated_monthly_cents: int


class PriceHikeAlertOut(BaseModel):
    recurring_id: int
    merchant: str
    previous_cents: int
    new_cents: int
    delta_pct: float
    tx_date: date


class InsightOut(BaseModel):
    severity: str
    title: str
    observation: str
    evidence: str
    why_useful: str
    outcome: str


class ForecastPointOut(BaseModel):
    horizon: str
    months: int
    projected_cash_cents: int
    cumulative_income_cents: int
    cumulative_expenses_cents: int
    cumulative_goal_savings_cents: int


class InsightsDashboardOut(BaseModel):
    insights: list[InsightOut]
    price_hike_alerts: list[PriceHikeAlertOut] = []
    recurring: list[RecurringSavedOut]
    recurring_suggestions: list[RecurringItemOut]
    forecast: list[ForecastPointOut]
    monthly_income_basis_cents: int
    monthly_expense_basis_cents: int


class ScenarioRequest(BaseModel):
    extra_monthly_savings_cents: int = 0
    monthly_income_delta_cents: int = 0


class ScenarioComparisonOut(BaseModel):
    baseline: list[ForecastPointOut]
    alternative: list[ForecastPointOut]
    five_year_difference_cents: int


class HoldingCreate(BaseModel):
    symbol: str
    name: str
    asset_type: str = "ETF"
    units: Decimal
    avg_cost_cents: int
    current_price_cents: int


class HoldingOut(BaseModel):
    holding_id: int
    symbol: str
    name: str
    asset_type: str
    units: Decimal
    cost_basis_cents: int
    market_value_cents: int
    gain_loss_cents: int
    gain_loss_pct: Decimal


class SuperUpdate(BaseModel):
    fund_name: str
    balance_cents: int
    personal_monthly_cents: int = 0
    expected_return_bps: int = 700


class SuperProjectionOut(BaseModel):
    years: int
    projected_balance_cents: int


class WealthDashboardOut(BaseModel):
    cash_cents: int
    investments_value_cents: int
    investments_cost_cents: int
    investments_gain_loss_cents: int
    super_fund_name: str
    super_balance_cents: int
    super_personal_monthly_cents: int
    super_expected_return_bps: int
    net_worth_cents: int
    holdings: list[HoldingOut]
    super_projections: list[SuperProjectionOut]


class HoldingPriceUpdate(BaseModel):
    current_price_cents: int
    units: Decimal | None = None


class SalaryReconciliationOut(BaseModel):
    employer_name: str
    pay_frequency: str
    expected_net_period_cents: int
    actual_avg_period_cents: int
    ytd_actual_salary_cents: int
    salary_deposit_count: int
    variance_cents: int


class WfhLogCreate(BaseModel):
    work_date: date
    hours: float
    note: str = ""


class WfhLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    work_date: date
    hours: float
    note: str


class TaxDeductionsDashboardOut(BaseModel):
    financial_year: str
    wfh_hours_total: float
    wfh_deduction_cents: int
    expense_deduction_cents: int
    total_claimable_cents: int
    wfh_logs: list[WfhLogOut]
    deductible_transactions: list[TransactionOut]
