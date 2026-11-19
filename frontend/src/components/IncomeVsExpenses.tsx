import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { MonthlyTrendPoint, Summary, formatAudFromCents } from "../api/client";

interface Props {
  trend: MonthlyTrendPoint[];
  summary: Summary;
  onGoToTaxEngine?: () => void;
}

export function IncomeVsExpenses({ trend, summary, onGoToTaxEngine }: Props) {
  const chartData = trend.map((pt) => ({
    month: pt.month.slice(5) + "/" + pt.month.slice(2, 4),
    Income: pt.income_cents / 100,
    Spend: pt.expenses_cents / 100,
    Savings: pt.net_savings_cents / 100,
  }));

  const meanSavingsCents =
    trend.length > 0
      ? Math.round(
          trend.reduce((acc, pt) => acc + pt.net_savings_cents, 0) / trend.length
        )
      : 0;

  return (
    <div className="lg:col-span-6 bg-surface-card border border-primary/20 p-6 md:p-8 flex flex-col justify-between">
      <div>
        <div className="flex items-start justify-between mb-6 pb-4 border-b border-primary/10">
          <div>
            <div className="text-[10px] text-secondary uppercase tracking-widest mb-1 font-bold font-display">
              .04. Trajectory Curve
            </div>
            <h2 className="heading-display text-2xl font-bold text-primary">
              Income vs. Spending
            </h2>
          </div>
          <div className="flex items-center gap-3 text-[11px] font-medium">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 bg-secondary" />
              <span className="text-on-surface-variant font-semibold">Income</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 bg-terracotta/80" />
              <span className="text-on-surface-variant font-semibold">Spend</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-0.5 bg-primary" />
              <span className="text-primary font-bold">Savings</span>
            </div>
          </div>
        </div>

        <p className="text-xs text-on-surface-variant mb-4 leading-relaxed font-normal">
          Historical overview across the previous {trend.length || 6} monthly cycles.
          Salary inflows and net surplus are tracked excluding internal transfers.
        </p>

        <div className="w-full bg-surface-low border border-primary/15 p-4 relative mb-4">
          <div className="flex justify-between text-[10px] text-on-surface-subtle mb-3 uppercase font-semibold">
            <span>{trend.length}-Mo Window</span>
            <span>
              Mean Savings: {meanSavingsCents >= 0 ? "+" : ""}
              {formatAudFromCents(meanSavingsCents)}/Mo
            </span>
            <span>ATO FY 26–27 Calibrated</span>
          </div>

          <div className="w-full h-56">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                <CartesianGrid strokeDasharray="2 2" stroke="#1B382B" strokeOpacity={0.1} />
                <XAxis
                  dataKey="month"
                  tick={{ fill: "#5C6B61", fontSize: 10, fontFamily: "Space Grotesk" }}
                  axisLine={{ stroke: "#1B382B", strokeOpacity: 0.15 }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: "#87968D", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v: number) => `$${Math.round(v / 1000)}k`}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#FAF8F5",
                    borderColor: "#1B382B",
                    borderRadius: 0,
                    fontSize: "12px",
                  }}
                  formatter={(val) => formatAudFromCents(Math.round(Number(val) * 100))}
                />
                <Bar dataKey="Income" fill="#7D9A83" barSize={16} />
                <Bar dataKey="Spend" fill="#C86452" fillOpacity={0.8} barSize={16} />
                <Line
                  type="monotone"
                  dataKey="Savings"
                  stroke="#1B382B"
                  strokeWidth={2}
                  dot={{ r: 3.5, fill: "#FFFFFF", stroke: "#1B382B", strokeWidth: 1.5 }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2 border border-primary/15 p-3 bg-surface text-center">
          <div className="border-r border-primary/10">
            <span className="block text-[10px] text-on-surface-subtle uppercase font-semibold">
              Month In
            </span>
            <span className="font-display text-xs font-bold text-secondary tabular-nums">
              +{formatAudFromCents(summary.income_cents)}
            </span>
          </div>
          <div className="border-r border-primary/10">
            <span className="block text-[10px] text-on-surface-subtle uppercase font-semibold">
              Month Out
            </span>
            <span className="font-display text-xs font-bold text-terracotta tabular-nums">
              -{formatAudFromCents(summary.expenses_cents)}
            </span>
          </div>
          <div>
            <span className="block text-[10px] text-on-surface-subtle uppercase font-semibold">
              Net Surplus
            </span>
            <span className="font-display text-xs font-bold text-primary tabular-nums">
              {summary.net_savings_cents >= 0 ? "+" : ""}
              {formatAudFromCents(summary.net_savings_cents)}
            </span>
          </div>
        </div>
      </div>

      <div className="mt-6 pt-4 border-t border-primary/10 flex items-center justify-between text-[11px] text-on-surface-variant">
        <span className="font-medium">
          Period: {summary.start_date} → {summary.end_date}
        </span>
        {onGoToTaxEngine && (
          <button
            className="text-primary hover:underline font-bold flex items-center gap-1 font-display"
            onClick={onGoToTaxEngine}
            type="button"
          >
            <span>Historical AUD Engine</span>
            <span className="material-symbols-outlined text-[13px]">arrow_right_alt</span>
          </button>
        )}
      </div>
    </div>
  );
}
