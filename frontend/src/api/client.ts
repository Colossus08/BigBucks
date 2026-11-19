const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000/api";

export interface Account {
  id: number;
  institution_id: number;
  name: string;
  account_number_mask: string;
  type: string;
  is_own: boolean;
  current_balance_cents: number;
}

export interface Category {
  id: number;
  name: string;
  group: string;
  parent_id: number | null;
  is_income: boolean;
  is_system: boolean;
}

export interface Transaction {
  id: number;
  account_id: number;
  date: string;
  amount_cents: number;
  description_raw: string;
  merchant: string;
  balance_cents: number | null;
  category_id: number | null;
  category_name: string;
  category_group: string;
  kind: string;
  is_transfer: boolean;
  paired_transaction_id?: number | null;
  is_tax_deductible?: boolean;
  deduction_category?: string | null;
  receipt_ref?: string | null;
  category_source: string;
}

export interface Summary {
  period: string;
  start_date: string;
  end_date: string;
  bank_balance_cents: number;
  upcoming_bills_cents: number;
  planned_goals_cents: number;
  safe_to_spend_cents: number;
  days_until_payday: number;
  daily_burn_rate_cents: number;
  available_to_spend_cents: number;
  income_cents: number;
  gross_expenses_cents: number;
  refunds_cents: number;
  reimbursements_cents: number;
  unclassified_in_cents: number;
  expenses_cents: number;
  moved_to_savings_cents: number;
  net_savings_cents: number;
  savings_rate_pct: string;
  uncategorised_count: number;
  by_group: Record<string, number>;
  by_category: Array<{
    category_id: number | null;
    category_name: string;
    category_group: string;
    total_cents: number;
  }>;
}

export interface MonthlyTrendPoint {
  month: string;
  income_cents: number;
  expenses_cents: number;
  net_savings_cents: number;
}

export interface IncomeEstimate {
  employer_name: string;
  pay_frequency: string;
  periods_per_year: number;
  gross_annual: string;
  gross_period: string;
  income_tax_period: string;
  medicare_levy_period: string;
  total_tax_period: string;
  net_period: string;
  super_annual: string;
  super_period: string;
  tax_year: string;
}

export interface ImportReport {
  batch_id: number;
  filename: string;
  total_rows: number;
  inserted_rows: number;
  duplicate_rows: number;
  error_rows: number;
  errors: Array<{ row_number: number; raw_line: string; reason: string }>;
  balance_warnings?: string[];
}

export interface UncategorisedMerchant {
  merchant: string;
  count: number;
  total_cents: number;
  sample_description: string;
  sample_transaction_id: number;
}

export interface SavingsAccount {
  id: number;
  name: string;
  net_moved_cents: number;
  transfer_count: number;
}

export interface TransferSuggestion {
  mask: string;
  count: number;
  net_moved_cents: number;
}

export interface Rule {
  id: number;
  pattern: string;
  match_type: string;
  category_id: number;
  category_name: string;
  priority: number;
  source: string;
  is_active: boolean;
}

export interface BudgetEval {
  budget_id: number;
  category_id: number;
  category_name: string;
  category_group: string;
  period: string;
  limit_cents: number;
  spent_cents: number;
  remaining_cents: number;
  pct_used: string;
  projected_cents?: number | null;
  status: "ok" | "warning" | "over";
  name?: string;
}

export interface BudgetRecommendation {
  category_id: number;
  category_name: string;
  category_group: string;
  avg_monthly_cents: number;
  recommended_monthly_cents: number;
  reasoning: string;
}

export interface CategoryHistoricalSpend {
  category_id: number;
  category_name: string;
  category_group: string;
  avg_monthly_cents: number;
  avg_fortnightly_cents: number;
  current_month_cents: number;
}

export interface PayCyclePlan {
  pay_frequency: string;
  income_basis: "salary" | "historical" | "custom";
  net_period_cents: number;
  budgeted_expenses_cents: number;
  recurring_bills_cents: number;
  goal_contributions_cents: number;
  unallocated_cents: number;
  declared_net_fortnightly_cents: number;
  declared_net_monthly_cents: number;
  historical_income_fortnightly_cents: number;
  historical_income_monthly_cents: number;
  historical_expenses_fortnightly_cents: number;
  historical_expenses_monthly_cents: number;
  net_fortnightly_cents: number;
  net_monthly_cents: number;
  budgeted_fortnightly_cents: number;
  budgeted_monthly_cents: number;
  recurring_bills_fortnightly_cents: number;
  recurring_bills_monthly_cents: number;
  goal_contributions_fortnightly_cents: number;
  goal_contributions_monthly_cents: number;
  unallocated_fortnightly_cents: number;
  unallocated_monthly_cents: number;
  category_averages: CategoryHistoricalSpend[];
}

export interface Goal {
  goal_id: number;
  name: string;
  category: string;
  total_target_cents: number;
  target_cents: number;
  extra_costs_cents: number;
  current_cents: number;
  remaining_cents: number;
  completion_pct: string;
  target_date: string | null;
  priority: number;
  planned_contribution_cents: number;
  contribution_frequency: string;
  linked_account_id: number | null;
  linked_account_name: string | null;
  linked_moved_cents: number;
  required_weekly_cents: number | null;
  required_fortnightly_cents: number | null;
  required_monthly_cents: number | null;
  projected_completion_date: string | null;
}

export interface RecurringItem {
  merchant: string;
  category_name: string;
  occurrences: number;
  avg_amount_cents: number;
  estimated_cadence: string;
  estimated_monthly_cents: number;
  last_date: string;
}

export interface RecurringSaved {
  id: number;
  merchant: string;
  category_name: string;
  amount_cents: number;
  cadence: string;
  estimated_monthly_cents: number;
}

export interface FinancialInsight {
  severity: "info" | "warning" | "positive";
  title: string;
  observation: string;
  evidence: string;
  why_useful: string;
  outcome: string;
}

export interface ForecastPoint {
  horizon: string;
  months: number;
  projected_cash_cents: number;
  cumulative_income_cents: number;
  cumulative_expenses_cents: number;
  cumulative_goal_savings_cents: number;
}

export interface PriceHikeAlert {
  recurring_id: number;
  merchant: string;
  previous_cents: number;
  new_cents: number;
  delta_pct: number;
  tx_date: string;
}

export interface InsightsDashboard {
  insights: FinancialInsight[];
  price_hike_alerts: PriceHikeAlert[];
  recurring: RecurringSaved[];
  recurring_suggestions: RecurringItem[];
  forecast: ForecastPoint[];
  monthly_income_basis_cents: number;
  monthly_expense_basis_cents: number;
}

export interface ScenarioComparison {
  baseline: ForecastPoint[];
  alternative: ForecastPoint[];
  five_year_difference_cents: number;
}

export interface Holding {
  holding_id: number;
  symbol: string;
  name: string;
  asset_type: string;
  units: string;
  cost_basis_cents: number;
  market_value_cents: number;
  gain_loss_cents: number;
  gain_loss_pct: string;
}

export interface WealthDashboard {
  cash_cents: number;
  investments_value_cents: number;
  investments_cost_cents: number;
  investments_gain_loss_cents: number;
  super_fund_name: string;
  super_balance_cents: number;
  super_personal_monthly_cents: number;
  super_expected_return_bps: number;
  net_worth_cents: number;
  holdings: Holding[];
  super_projections: Array<{ years: number; projected_balance_cents: number }>;
}

export interface SalaryReconciliation {
  employer_name: string;
  pay_frequency: string;
  expected_net_period_cents: number;
  actual_avg_period_cents: number;
  ytd_actual_salary_cents: number;
  salary_deposit_count: number;
  variance_cents: number;
}

export interface WfhLog {
  id: number;
  work_date: string;
  hours: number;
  note: string;
}

export interface TaxDeductionsDashboard {
  financial_year: string;
  wfh_hours_total: number;
  wfh_deduction_cents: number;
  expense_deduction_cents: number;
  total_claimable_cents: number;
  wfh_logs: WfhLog[];
  deductible_transactions: Transaction[];
}

const audFormatter = new Intl.NumberFormat("en-AU", {
  style: "currency",
  currency: "AUD",
});

export function formatAudFromCents(cents: number): string {
  return audFormatter.format(cents / 100);
}

export function formatAudFromDollars(dollars: string | number): string {
  return audFormatter.format(Number(dollars));
}

const AUTH_TOKEN_KEY = "finance_auth_token";
let onUnauthorizedHandler: (() => void) | null = null;

export function getAuthToken(): string | null {
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

export function setAuthToken(token: string): void {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
}

export function clearAuthToken(): void {
  localStorage.removeItem(AUTH_TOKEN_KEY);
}

export function setOnUnauthorized(handler: (() => void) | null): void {
  onUnauthorizedHandler = handler;
}

async function authFetch(path: string, init?: RequestInit): Promise<Response> {
  const token = getAuthToken();
  const headers = new Headers(init?.headers ?? {});
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (res.status === 401 && path !== "/auth/login" && path !== "/auth/status") {
    clearAuthToken();
    onUnauthorizedHandler?.();
  }
  return res;
}

function withTokenQuery(url: string): string {
  const token = getAuthToken();
  return token ? `${url}?token=${encodeURIComponent(token)}` : url;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await authFetch(path, init);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getAuthStatus: () =>
    request<{ auth_required: boolean; authenticated: boolean; username: string | null }>(
      "/auth/status"
    ),
  login: async (username: string, password: string) => {
    const res = await request<{ access_token: string; token_type: string; username: string }>(
      "/auth/login",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      }
    );
    setAuthToken(res.access_token);
    return res;
  },
  getAccounts: () => request<Account[]>("/accounts"),
  getSavingsAccounts: () => request<SavingsAccount[]>("/accounts/savings"),
  getTransferSuggestions: () => request<TransferSuggestion[]>("/accounts/transfer-suggestions"),
  trackSavingsAccount: (name: string, mask: string) =>
    request<Account>("/accounts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, account_number_mask: mask, type: "savings" }),
    }),
  deleteAccount: (accountId: number) =>
    authFetch(`/accounts/${accountId}`, { method: "DELETE" }),
  getTransactionCount: () => request<{ count: number }>("/transactions/count"),
  getCategories: () => request<Category[]>("/categories"),
  createCategory: (name: string, group: string, is_income = false) =>
    request<Category>("/categories", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, group, is_income }),
    }),
  deleteCategory: (categoryId: number) =>
    authFetch(`/categories/${categoryId}`, { method: "DELETE" }),
  getAvailableMonths: () => request<string[]>("/summary/months"),
  getSummary: (period = "month", anchorDate?: string) => {
    const params = new URLSearchParams({ period });
    if (anchorDate) params.set("date", anchorDate);
    return request<Summary>(`/summary?${params.toString()}`);
  },
  getTrend: (months = 6) => request<MonthlyTrendPoint[]>(`/summary/trend?months=${months}`),
  getIncomeEstimate: () => request<IncomeEstimate>("/income/estimate"),
  getTransactions: (filters?: { q?: string; category?: number; account?: number; limit?: number }) => {
    const params = new URLSearchParams();
    if (filters?.q) params.set("q", filters.q);
    if (filters?.category) params.set("category", String(filters.category));
    if (filters?.account) params.set("account", String(filters.account));
    if (filters?.limit) params.set("limit", String(filters.limit));
    return request<Transaction[]>(`/transactions?${params.toString()}`);
  },
  updateTransaction: (id: number, category_id: number, apply_to_merchant: boolean) =>
    request<{ transaction: Transaction; updated_count: number }>(`/transactions/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category_id, apply_to_merchant }),
    }),
  setTransactionExcluded: (id: number, excluded: boolean) =>
    request<{ transaction: Transaction; updated_count: number }>(`/transactions/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ excluded }),
    }),
  setTransactionTaxDeductible: (
    id: number,
    is_tax_deductible: boolean,
    deduction_category?: string | null
  ) =>
    request<{ transaction: Transaction; updated_count: number }>(`/transactions/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_tax_deductible, deduction_category }),
    }),
  splitTransaction: (
    id: number,
    split_amount_cents: number,
    category_id: number,
    note = ""
  ) =>
    request<{ parent: Transaction; child: Transaction }>(`/transactions/${id}/split`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ split_amount_cents, category_id, note }),
    }),
  unsplitTransaction: (id: number) =>
    request<Transaction>(`/transactions/${id}/unsplit`, {
      method: "POST",
    }),
  get exportTransactionsUrl() {
    return withTokenQuery(`${API_BASE}/exports/transactions.csv`);
  },
  get exportBackupUrl() {
    return withTokenQuery(`${API_BASE}/exports/backup.db`);
  },
  get exportTaxDeductionsUrl() {
    return withTokenQuery(`${API_BASE}/exports/tax-deductions.csv`);
  },
  getSalaryReconciliation: () =>
    request<SalaryReconciliation>("/income/reconciliation"),
  getTaxDeductions: (fy?: string) =>
    request<TaxDeductionsDashboard>(
      `/income/tax-deductions${fy ? `?fy=${encodeURIComponent(fy)}` : ""}`
    ),
  addWfhLog: (work_date: string, hours: number, note = "") =>
    request<WfhLog>("/income/wfh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ work_date, hours, note }),
    }),
  deleteWfhLog: (id: number) =>
    authFetch(`/income/wfh/${id}`, { method: "DELETE" }),
  importCommbankCsv: (accountId: number, file: File) => {
    const form = new FormData();
    form.append("account_id", String(accountId));
    form.append("file", file);
    return request<ImportReport>("/imports/commbank", {
      method: "POST",
      body: form,
    });
  },
  getUncategorisedMerchants: () =>
    request<UncategorisedMerchant[]>("/transactions/merchants/uncategorised"),
  createRule: (pattern: string, category_id: number) =>
    request<{ updated_count: number }>("/rules", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pattern, match_type: "contains", category_id }),
    }),
  reapplyRules: () =>
    request<{ updated_count: number }>("/rules/reapply", {
      method: "POST",
    }),
  getRules: () => request<Rule[]>("/rules"),
  undoLatestRule: () =>
    request<{ updated_count: number }>("/rules/undo-latest", {
      method: "POST",
    }),
  deleteRule: (ruleId: number) =>
    request<{ updated_count: number }>(`/rules/${ruleId}`, {
      method: "DELETE",
    }),
  updateRuleCategory: (ruleId: number, categoryId: number) =>
    request<{ updated_count: number }>(`/rules/${ruleId}?category_id=${categoryId}`, {
      method: "PATCH",
    }),
  bulkCategorise: (merchants: string[], category_id: number) =>
    request<{ updated_count: number }>("/transactions/bulk-categorise", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ merchants, category_id }),
    }),
  getBudgets: (month?: string) =>
    request<BudgetEval[]>(
      `/budgets${month ? `?month=${encodeURIComponent(month)}` : ""}`
    ),
  upsertBudget: (category_id: number, period: string, limit_cents: number, name = "") =>
    request<BudgetEval>("/budgets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category_id, period, limit_cents, name }),
    }),
  updateBudget: (
    budgetId: number,
    payload: { name?: string; period?: string; limit_cents?: number }
  ) =>
    request<BudgetEval>(`/budgets/${budgetId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  deleteBudget: (budgetId: number) =>
    authFetch(`/budgets/${budgetId}`, { method: "DELETE" }),
  getBudgetRecommendations: () =>
    request<BudgetRecommendation[]>("/budgets/recommendations"),
  getPayCyclePlan: (basis?: "salary" | "historical" | "custom", customFortnightlyCents?: number) => {
    const params = new URLSearchParams();
    if (basis) params.set("basis", basis);
    if (customFortnightlyCents && customFortnightlyCents > 0) {
      params.set("custom_fortnightly_cents", String(customFortnightlyCents));
    }
    const qs = params.toString();
    return request<PayCyclePlan>(`/budgets/pay-cycle${qs ? `?${qs}` : ""}`);
  },
  updateNetPay: (net_fortnightly_cents: number | null) =>
    request<PayCyclePlan>("/budgets/net-pay", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ net_fortnightly_cents }),
    }),
  getGoals: () => request<Goal[]>("/goals"),
  createGoal: (payload: {
    name: string;
    category: string;
    target_cents: number;
    extra_costs_cents: number;
    current_cents: number;
    target_date: string | null;
    priority: number;
    planned_contribution_cents: number;
    contribution_frequency: string;
    linked_account_id: number | null;
  }) =>
    request<Goal>("/goals", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  contributeGoal: (goalId: number, amount_cents: number, note = "") =>
    request<Goal>(`/goals/${goalId}/contribute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amount_cents, note }),
    }),
  deleteGoal: (goalId: number) =>
    authFetch(`/goals/${goalId}`, { method: "DELETE" }),
  updateGoal: (
    goalId: number,
    payload: {
      name?: string;
      category?: string;
      target_cents?: number;
      planned_contribution_cents?: number;
      linked_account_id?: number | null;
      clear_linked_account?: boolean;
    }
  ) =>
    request<Goal>(`/goals/${goalId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  updateIncomeProfile: (payload: {
    employer_name: string;
    gross_annual_cents: number;
    pay_frequency: string;
    super_rate_bps: number;
  }) =>
    request<IncomeEstimate>("/income/profile", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  getInsights: () => request<InsightsDashboard>("/insights"),
  addRecurring: (payload: {
    merchant: string;
    category_name: string;
    amount_cents: number;
    cadence: string;
  }) =>
    request<RecurringSaved>("/insights/recurring", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  deleteRecurring: (id: number) =>
    authFetch(`/insights/recurring/${id}`, { method: "DELETE" }),
  dismissRecurringSuggestion: (merchant: string, category_name: string) =>
    authFetch(`/insights/recurring/dismiss`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ merchant, category_name }),
    }),
  updateRecurringBaseline: (id: number, amount_cents: number) =>
    request<RecurringSaved>(`/insights/recurring/${id}?amount_cents=${amount_cents}`, {
      method: "PATCH",
    }),
  refreshHoldingPrice: (holdingId: number, current_price_cents: number) =>
    request<Holding>(`/wealth/holdings/${holdingId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_price_cents }),
    }),
  runScenario: (extra_monthly_savings_cents: number, monthly_income_delta_cents = 0) =>
    request<ScenarioComparison>("/insights/scenario", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ extra_monthly_savings_cents, monthly_income_delta_cents }),
    }),
  getWealth: () => request<WealthDashboard>("/wealth"),
  addHolding: (payload: {
    symbol: string;
    name: string;
    asset_type: string;
    units: number;
    avg_cost_cents: number;
    current_price_cents: number;
  }) =>
    request<Holding>("/wealth/holdings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  deleteHolding: (holdingId: number) =>
    authFetch(`/wealth/holdings/${holdingId}`, { method: "DELETE" }),
  updateSuper: (payload: {
    fund_name: string;
    balance_cents: number;
    personal_monthly_cents: number;
    expected_return_bps: number;
  }) =>
    request<WealthDashboard>("/wealth/super", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
};
