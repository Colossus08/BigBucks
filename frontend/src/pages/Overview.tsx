import {
  Account,
  Category,
  MonthlyTrendPoint,
  Summary,
  Transaction,
  formatAudFromCents,
} from "../api/client";
import { IncomeVsExpenses } from "../components/IncomeVsExpenses";
import { SpendingDonut } from "../components/SpendingDonut";

interface Props {
  accounts: Account[];
  summary: Summary | null;
  period: "month" | "year" | "all";
  availableMonths: string[];
  selectedMonth: string;
  onPeriodChange: (period: "month" | "year" | "all", month?: string) => void;
  trend: MonthlyTrendPoint[];
  recentTransactions: Transaction[];
  categories: Category[];
  onDataChanged: () => Promise<void>;
  onGoToTaxEngine: () => void;
  onGoToUncategorised: () => void;
}

function formatShortDate(iso: string): string {
  const parts = iso.split("-");
  if (parts.length !== 3) return iso;
  const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" });
}

function formatMonthName(ym: string): string {
  const parts = ym.split("-");
  if (parts.length < 2) return ym;
  const d = new Date(Number(parts[0]), Number(parts[1]) - 1, 1);
  if (Number.isNaN(d.getTime())) return ym;
  return d.toLocaleDateString("en-AU", { month: "long", year: "numeric" });
}

export function Overview({
  accounts,
  summary,
  period,
  availableMonths,
  selectedMonth,
  onPeriodChange,
  trend,
  onGoToTaxEngine,
  onGoToUncategorised,
}: Props) {
  if (!summary) {
    return (
      <div className="bg-surface-card border border-primary/20 p-8 text-sm text-on-surface-variant">
        Loading financial overview...
      </div>
    );
  }

  const monthName = formatMonthName(summary.start_date.slice(0, 7));

  const periodLabel =
    period === "all"
      ? "All Time"
      : period === "year"
        ? `Year ${summary.start_date.slice(0, 4)}`
        : monthName;

  const analysisBannerText =
    period === "all"
      ? "Showing analysis for all uploaded transactions (All Time)"
      : period === "year"
        ? `Showing analysis for the full year ${summary.start_date.slice(0, 4)} (${formatShortDate(summary.start_date)} – ${formatShortDate(summary.end_date)})`
        : `Showing analysis for the month of ${monthName} (${formatShortDate(summary.start_date)} – ${formatShortDate(summary.end_date)})`;

  const spentParts: string[] = [];
  if (summary.reimbursements_cents > 0) {
    spentParts.push(`${formatAudFromCents(summary.reimbursements_cents)} reimbursed`);
  }
  if (summary.refunds_cents > 0) {
    spentParts.push(`${formatAudFromCents(summary.refunds_cents)} refunded`);
  }
  const spentSub =
    spentParts.length > 0
      ? `Gross ${formatAudFromCents(summary.gross_expenses_cents + summary.refunds_cents)} · ${spentParts.join(", ")}`
      : "Excludes internal transfers";

  const primaryAccount = accounts[0];

  return (
    <div className="space-y-10">
      {/* Header & Period Controls */}
      <section className="pb-6 border-b border-primary/15 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 text-[11px] text-on-surface-variant uppercase tracking-wider mb-3 font-semibold">
            <span className="text-terracotta font-bold">.01.</span>
            <span>{primaryAccount?.name ?? "Smart Access"}</span>
            <span className="text-primary/30">/</span>
            <span className="text-secondary font-bold">
              {periodLabel}
            </span>
          </div>
          <h1 className="heading-display text-3xl md:text-4xl text-primary font-bold">
            Financial Position Overview
          </h1>
          <p className="text-xs text-on-surface-variant mt-1.5 font-medium">
            {analysisBannerText}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {availableMonths.length > 0 && (
            <select
              className="select text-xs font-bold uppercase font-display"
              value={period === "month" ? selectedMonth : ""}
              onChange={(e) => {
                if (e.target.value) {
                  onPeriodChange("month", e.target.value);
                }
              }}
            >
              {availableMonths.map((ym) => (
                <option key={ym} value={ym}>
                  Month: {formatMonthName(ym)}
                </option>
              ))}
            </select>
          )}
          {(["month", "year", "all"] as const).map((p) => (
            <button
              key={p}
              className={`px-3.5 py-2 text-xs font-bold uppercase tracking-wider font-display border transition-colors ${
                period === p
                  ? "bg-primary text-white border-primary"
                  : "bg-surface-card text-primary border-primary/20 hover:bg-surface-low"
              }`}
              onClick={() => onPeriodChange(p)}
              type="button"
            >
              {p === "month" ? "Monthly" : p === "year" ? "Full Year" : "All Time"}
            </button>
          ))}
        </div>
      </section>

      {summary.uncategorised_count > 0 && (
        <div className="bg-surface-low border border-warm-gold/40 p-4 flex flex-wrap items-center justify-between gap-3">
          <span className="text-xs text-primary font-medium">
            <strong>{summary.uncategorised_count}</strong> uncategorised transaction(s) in {periodLabel}
            {summary.unclassified_in_cents > 0 && (
              <>
                {" "}
                (including <strong>{formatAudFromCents(summary.unclassified_in_cents)}</strong>{" "}
                incoming not yet counted as income)
              </>
            )}
            .
          </span>
          <button
            className="bg-primary text-white px-4 py-1.5 text-xs font-bold uppercase tracking-wider font-display"
            onClick={onGoToUncategorised}
            type="button"
          >
            Review &amp; Categorise
          </button>
        </div>
      )}

      {/* Key Metrics */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-surface-card border border-primary/20 p-5">
          <div className="text-[10px] text-on-surface-subtle uppercase tracking-widest font-bold mb-2">
            Account Balance
          </div>
          <div className="font-display text-2xl font-bold text-primary tabular-nums">
            {formatAudFromCents(summary.bank_balance_cents)}
          </div>
          <div className="text-[11px] text-on-surface-variant mt-1">
            {primaryAccount?.name ?? "Smart Access"} closing balance
          </div>
        </div>

        <div className="bg-surface-card border border-primary/20 p-5">
          <div className="text-[10px] text-on-surface-subtle uppercase tracking-widest font-bold mb-2">
            Income ({periodLabel})
          </div>
          <div className="font-display text-2xl font-bold text-secondary tabular-nums">
            {formatAudFromCents(summary.income_cents)}
          </div>
          <div className="text-[11px] text-on-surface-variant mt-1">
            Excludes transfers &amp; reimbursements
          </div>
        </div>

        <div className="bg-surface-card border border-primary/20 p-5">
          <div className="text-[10px] text-on-surface-subtle uppercase tracking-widest font-bold mb-2">
            Net Spent ({periodLabel})
          </div>
          <div className="font-display text-2xl font-bold text-terracotta tabular-nums">
            {formatAudFromCents(summary.expenses_cents)}
          </div>
          <div className="text-[11px] text-on-surface-variant mt-1">{spentSub}</div>
        </div>

        <div className="bg-surface-card border border-primary/20 p-5">
          <div className="text-[10px] text-on-surface-subtle uppercase tracking-widest font-bold mb-2">
            Net Saved
          </div>
          <div className="font-display text-2xl font-bold text-primary tabular-nums">
            {formatAudFromCents(summary.net_savings_cents)}
          </div>
          <div className="text-[11px] text-on-surface-variant mt-1">
            Savings rate: {summary.savings_rate_pct}%
            {summary.moved_to_savings_cents !== 0 &&
              ` · Moved to savings: ${formatAudFromCents(summary.moved_to_savings_cents)}`}
          </div>
        </div>
      </section>

      {/* Charts */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <SpendingDonut summary={summary} />
        <IncomeVsExpenses trend={trend} summary={summary} onGoToTaxEngine={onGoToTaxEngine} />
      </section>
    </div>
  );
}
