import { useEffect, useState } from "react";
import {
  Account,
  Category,
  IncomeEstimate,
  MonthlyTrendPoint,
  Summary,
  Transaction,
  api,
  clearAuthToken,
  setOnUnauthorized,
} from "./api/client";
import { ImportModal } from "./components/ImportModal";
import { Accounts } from "./pages/Accounts";
import { Budget } from "./pages/Budget";
import { Goals } from "./pages/Goals";
import { Insights } from "./pages/Insights";
import { Login } from "./pages/Login";
import { Overview } from "./pages/Overview";
import { TaxAndEngine } from "./pages/TaxAndEngine";
import { Transactions } from "./pages/Transactions";
import { Wealth } from "./pages/Wealth";

type Tab =
  | "overview"
  | "budget"
  | "goals"
  | "insights"
  | "wealth"
  | "tax"
  | "transactions"
  | "categories"
  | "accounts";

export function App() {
  const [tab, setTab] = useState<Tab>("overview");
  const [period, setPeriod] = useState<"month" | "year" | "all">("month");
  const [availableMonths, setAvailableMonths] = useState<string[]>([]);
  const [selectedMonth, setSelectedMonth] = useState<string>("");
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [trend, setTrend] = useState<MonthlyTrendPoint[]>([]);
  const [incomeEstimate, setIncomeEstimate] = useState<IncomeEstimate | null>(null);
  const [allTransactions, setAllTransactions] = useState<Transaction[]>([]);
  const [txCount, setTxCount] = useState<number>(0);
  const [txCategoryFilter, setTxCategoryFilter] = useState<number | undefined>(undefined);
  const [importOpen, setImportOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authChecking, setAuthChecking] = useState(true);
  const [authRequired, setAuthRequired] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);

  const refreshAll = async (
    selectedPeriod: "month" | "year" | "all" = period,
    monthOverride?: string
  ) => {
    try {
      setError(null);
      const anchorDate =
        selectedPeriod === "month" && (monthOverride ?? selectedMonth)
          ? `${monthOverride ?? selectedMonth}-15`
          : undefined;
      const [acc, cats, sum, tr, inc, txs, countRes, months] = await Promise.all([
        api.getAccounts(),
        api.getCategories(),
        api.getSummary(selectedPeriod, anchorDate),
        api.getTrend(6),
        api.getIncomeEstimate(),
        api.getTransactions({ limit: 50 }),
        api.getTransactionCount(),
        api.getAvailableMonths(),
      ]);
      setAccounts(acc);
      setCategories(cats);
      setSummary(sum);
      setTrend(tr);
      setIncomeEstimate(inc);
      setAllTransactions(txs);
      setTxCount(countRes.count);
      setAvailableMonths(months);
      if (!selectedMonth && months.length > 0 && !monthOverride) {
        setSelectedMonth(months[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to connect to backend API");
    }
  };

  useEffect(() => {
    setOnUnauthorized(() => {
      setAuthenticated(false);
    });
    const init = async () => {
      try {
        const st = await api.getAuthStatus();
        setAuthRequired(st.auth_required);
        setAuthenticated(st.authenticated);
        if (!st.auth_required || st.authenticated) {
          await refreshAll();
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to connect to backend API");
      } finally {
        setAuthChecking(false);
      }
    };
    void init();
    return () => setOnUnauthorized(null);
  }, []);

  if (authChecking) {
    return (
      <div className="min-h-screen bg-surface text-on-surface flex items-center justify-center text-sm text-on-surface-variant">
        Loading...
      </div>
    );
  }

  if (authRequired && !authenticated) {
    return (
      <Login
        onSuccess={async () => {
          setAuthenticated(true);
          await refreshAll();
        }}
      />
    );
  }

  const uncatId = categories.find((c) => c.name === "Uncategorised")?.id;
  const primaryAccount = accounts[0];

  const topNavItems: Array<{ id: Tab; label: string }> = [
    { id: "overview", label: "Overview" },
    { id: "budget", label: "Budget" },
    { id: "goals", label: "Goals" },
    { id: "insights", label: "Insights" },
    { id: "wealth", label: "Wealth" },
  ];

  const openLedgerView = (
    target: "transactions" | "categories" | "accounts" | "tax"
  ) => {
    setTxCategoryFilter(target === "categories" ? uncatId : undefined);
    setTab(target);
    setSettingsOpen(false);
  };

  return (
    <div className="min-h-screen flex flex-col bg-surface text-on-surface relative">
      {/* Editorial Upper Navigation Header */}
      <header className="w-full border-b border-primary/15 bg-surface/90 backdrop-blur-sm sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-6 md:px-12 h-20 flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <button
              className="flex items-center gap-3 group text-left"
              onClick={() => setTab("overview")}
              type="button"
            >
              <div className="w-7 h-7 border border-primary flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-white transition-colors duration-200">
                <span className="font-display font-bold text-xs">AT</span>
              </div>
              <div className="flex flex-col">
                <span className="text-xs font-bold tracking-[0.2em] text-primary uppercase font-display">
                  Aaron Thomas
                </span>
                <span className="text-[10px] text-on-surface-subtle tracking-wider font-medium uppercase">
                  {primaryAccount?.name ?? "CommBank Smart Access"}
                </span>
              </div>
            </button>
            <div className="hidden xl:flex items-center gap-2 pl-4 border-l border-primary/15">
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  error ? "bg-terracotta" : "bg-secondary"
                }`}
              />
              <span className="text-[11px] text-on-surface-variant tracking-wider uppercase font-medium">
                {error ? "API Offline" : `SQLite ${txCount} Synced`}
              </span>
            </div>
          </div>

          {/* Center Minimal Navigation Bar */}
          <nav className="hidden md:flex items-center space-x-7">
            {topNavItems.map((item) => {
              const active = tab === item.id;
              return (
                <button
                  key={item.id}
                  className={`group relative py-2 text-xs tracking-wider uppercase font-display transition-colors flex items-center gap-1.5 ${
                    active
                      ? "font-bold text-primary"
                      : "font-semibold text-on-surface-variant hover:text-primary"
                  }`}
                  onClick={() => setTab(item.id)}
                  type="button"
                >
                  <span>{item.label}</span>
                  {active ? (
                    <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-primary" />
                  ) : (
                    <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-primary opacity-0 group-hover:opacity-100 transition-opacity" />
                  )}
                </button>
              );
            })}
          </nav>

          {/* Right Action Tools: Import + Settings/Ledger Sidebar */}
          <div className="flex items-center gap-3">
            <button
              className="hidden sm:flex items-center gap-2 border border-primary/25 bg-surface-card px-3.5 py-2 hover:bg-surface-low transition-colors text-xs font-bold text-primary tracking-wider uppercase font-display"
              onClick={() => setImportOpen(true)}
              type="button"
            >
              <span className="material-symbols-outlined text-[16px]">file_upload</span>
              <span>Import CSV</span>
            </button>
            <button
              className={`flex items-center gap-2 border px-3.5 py-2 transition-colors text-xs font-bold tracking-wider uppercase font-display ${
                tab === "transactions" || tab === "categories" || tab === "accounts" || settingsOpen
                  ? "bg-primary text-white border-primary"
                  : "border-primary/25 bg-surface-card text-primary hover:bg-surface-low"
              }`}
              onClick={() => setSettingsOpen(true)}
              type="button"
            >
              <span className="material-symbols-outlined text-[16px]">tune</span>
              <span>Ledger &amp; Settings</span>
            </button>
            {authRequired && (
              <button
                className="border border-primary/25 bg-surface-card px-3 py-2 hover:bg-surface-low transition-colors text-xs font-bold text-on-surface-variant hover:text-primary tracking-wider uppercase font-display"
                onClick={() => {
                  clearAuthToken();
                  setAuthenticated(false);
                }}
                type="button"
              >
                Sign Out
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Body Frame */}
      <main className="max-w-7xl w-full mx-auto px-6 md:px-12 py-10 flex-1">
        {error && (
          <div className="banner">
            <span>API connection error: {error}</span>
            <button className="btn" onClick={() => void refreshAll()} type="button">
              Retry
            </button>
          </div>
        )}

        {tab === "overview" && (
          <Overview
            accounts={accounts}
            availableMonths={availableMonths}
            categories={categories}
            onDataChanged={refreshAll}
            onGoToTaxEngine={() => setTab("tax")}
            onGoToUncategorised={() => openLedgerView("categories")}
            period={period}
            selectedMonth={selectedMonth}
            onPeriodChange={(next, month) => {
              setPeriod(next);
              if (month) setSelectedMonth(month);
              void refreshAll(next, month);
            }}
            recentTransactions={allTransactions}
            summary={summary}
            trend={trend}
          />
        )}

        {(tab === "transactions" || tab === "categories") && (
          <Transactions
            accounts={accounts}
            categories={categories}
            initialCategoryFilter={txCategoryFilter}
            onDataChanged={refreshAll}
          />
        )}

        {tab === "tax" && (
          <TaxAndEngine incomeEstimate={incomeEstimate} onDataChanged={refreshAll} />
        )}

        {tab === "budget" && <Budget categories={categories} />}
        {tab === "goals" && <Goals />}
        {tab === "insights" && <Insights />}
        {tab === "wealth" && <Wealth />}
        {tab === "accounts" && <Accounts onDataChanged={refreshAll} />}
      </main>

      {/* Clean Editorial Footer */}
      <footer className="w-full border-t border-primary/15 py-8 bg-surface">
        <div className="max-w-7xl mx-auto px-6 md:px-12 flex flex-col md:flex-row items-center justify-between gap-4 text-[11px] text-on-surface-variant">
          <div className="flex items-center gap-4 font-medium">
            <span>© 2026 Aaron Thomas</span>
            <span>•</span>
            <span>Personal Ledger</span>
          </div>

          <div className="flex items-center gap-2 text-primary">
            <span className="text-[10px]">❖</span>
            <span className="font-display font-bold text-xs tracking-widest uppercase">
              Atelier CommBank
            </span>
            <span className="text-[10px]">❖</span>
          </div>

          <div className="flex items-center gap-6">
            <span className="text-secondary font-bold">
              {incomeEstimate?.tax_year ?? "ATO FY 2026–27"} Engine
            </span>
            <span className="uppercase tracking-wider font-bold font-display text-primary">
              Local Host
            </span>
          </div>
        </div>
      </footer>

      {/* Slide-out Ledger & Settings Sidebar */}
      {settingsOpen && (
        <div
          className="fixed inset-0 z-50 bg-primary/35 backdrop-blur-xs flex justify-end"
          onClick={() => setSettingsOpen(false)}
        >
          <aside
            className="w-full max-w-sm bg-surface-card border-l border-primary/25 h-full p-7 flex flex-col justify-between shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div>
              <div className="flex items-center justify-between pb-4 mb-6 border-b border-primary/15">
                <div>
                  <span className="text-[10px] text-secondary uppercase tracking-widest font-bold font-display">
                    Ledger &amp; Settings
                  </span>
                  <h2 className="heading-display text-2xl text-primary font-bold">
                    Manage Data
                  </h2>
                </div>
                <button
                  className="text-on-surface-subtle hover:text-primary"
                  onClick={() => setSettingsOpen(false)}
                  type="button"
                >
                  <span className="material-symbols-outlined">close</span>
                </button>
              </div>

              <div className="space-y-3">
                <button
                  className="w-full text-left border border-primary/20 bg-surface p-4 hover:bg-surface-low transition-colors"
                  onClick={() => openLedgerView("transactions")}
                  type="button"
                >
                  <div className="text-xs font-bold uppercase tracking-wider text-primary font-display">
                    Transactions Ledger
                  </div>
                  <div className="text-xs text-on-surface-variant mt-1">
                    Search, filter, and inspect all {txCount} synced entries.
                  </div>
                </button>

                <button
                  className="w-full text-left border border-primary/20 bg-surface p-4 hover:bg-surface-low transition-colors"
                  onClick={() => openLedgerView("categories")}
                  type="button"
                >
                  <div className="text-xs font-bold uppercase tracking-wider text-primary font-display">
                    Categories &amp; Quick Rules
                  </div>
                  <div className="text-xs text-on-surface-variant mt-1">
                    Bulk-categorise merchants, add keyword rules, or undo recent rules.
                  </div>
                </button>

                <button
                  className="w-full text-left border border-primary/20 bg-surface p-4 hover:bg-surface-low transition-colors"
                  onClick={() => openLedgerView("accounts")}
                  type="button"
                >
                  <div className="text-xs font-bold uppercase tracking-wider text-primary font-display">
                    Savings Accounts
                  </div>
                  <div className="text-xs text-on-surface-variant mt-1">
                    Track transfers to your savings accounts and link them to goals.
                  </div>
                </button>

                <button
                  className="w-full text-left border border-primary/20 bg-surface p-4 hover:bg-surface-low transition-colors"
                  onClick={() => openLedgerView("tax")}
                  type="button"
                >
                  <div className="text-xs font-bold uppercase tracking-wider text-primary font-display">
                    Tax &amp; Rule Engine
                  </div>
                  <div className="text-xs text-on-surface-variant mt-1">
                    Salary &amp; super tax breakdown and classification rule registry.
                  </div>
                </button>

                <button
                  className="w-full text-left border border-primary/20 bg-surface p-4 hover:bg-surface-low transition-colors"
                  onClick={() => {
                    setSettingsOpen(false);
                    setImportOpen(true);
                  }}
                  type="button"
                >
                  <div className="text-xs font-bold uppercase tracking-wider text-primary font-display">
                    Import NetBank CSV
                  </div>
                  <div className="text-xs text-on-surface-variant mt-1">
                    Upload a new CommBank export (duplicates skipped automatically).
                  </div>
                </button>

                <div className="grid grid-cols-2 gap-2 pt-2">
                  <a
                    className="text-center border border-primary/20 bg-surface p-2.5 hover:bg-surface-low transition-colors text-[11px] font-bold uppercase tracking-wider text-primary font-display"
                    href={api.exportTransactionsUrl}
                  >
                    Export CSV
                  </a>
                  <a
                    className="text-center border border-primary/20 bg-surface p-2.5 hover:bg-surface-low transition-colors text-[11px] font-bold uppercase tracking-wider text-primary font-display"
                    href={api.exportBackupUrl}
                  >
                    Backup DB
                  </a>
                </div>
              </div>
            </div>

            <div className="pt-5 border-t border-primary/15 text-xs text-on-surface-variant space-y-1">
              <div className="font-bold text-primary uppercase tracking-wider text-[10px]">
                Connected Account
              </div>
              <div>{primaryAccount?.name ?? "Smart Access"}</div>
              <div>Database: Local SQLite</div>
            </div>
          </aside>
        </div>
      )}

      <ImportModal
        accounts={accounts}
        onClose={() => setImportOpen(false)}
        onImported={refreshAll}
        open={importOpen}
      />
    </div>
  );
}

export default App;
