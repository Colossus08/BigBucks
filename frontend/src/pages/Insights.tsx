import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { InsightsDashboard, ScenarioComparison, api, formatAudFromCents } from "../api/client";

export function Insights() {
  const [data, setData] = useState<InsightsDashboard | null>(null);
  const [extraFortnightly, setExtraFortnightly] = useState("100");
  const [incomeDeltaMonthly, setIncomeDeltaMonthly] = useState("0");
  const [scenario, setScenario] = useState<ScenarioComparison | null>(null);

  // Manual recurring form
  const [recMerchant, setRecMerchant] = useState("");
  const [recCategory, setRecCategory] = useState("Subscription services");
  const [recAmount, setRecAmount] = useState("");
  const [recCadence, setRecCadence] = useState("Monthly");
  const [dismissedMerchants, setDismissedMerchants] = useState<string[]>([]);

  const load = async () => {
    const res = await api.getInsights();
    setData(res);
  };

  useEffect(() => {
    void load();
  }, []);

  const handleRunScenario = async () => {
    const extraMonthlyCents = Math.round((Number(extraFortnightly || 0) * 26) / 12 * 100);
    const incomeDeltaCents = Math.round(Number(incomeDeltaMonthly || 0) * 100);
    setScenario(await api.runScenario(extraMonthlyCents, incomeDeltaCents));
  };

  const handleAddManualRecurring = async () => {
    if (!recMerchant.trim() || !recAmount) return;
    const cents = Math.round(Number(recAmount) * 100);
    if (cents <= 0) return;
    await api.addRecurring({
      merchant: recMerchant.trim(),
      category_name: recCategory,
      amount_cents: cents,
      cadence: recCadence,
    });
    setRecMerchant("");
    setRecAmount("");
    await load();
  };

  if (!data) {
    return (
      <div className="bg-surface-card border border-primary/20 p-8 text-sm text-on-surface-variant">
        Loading financial intelligence...
      </div>
    );
  }

  const forecastChartData = (scenario ? scenario.baseline : data.forecast).map((pt, idx) => ({
    horizon: pt.horizon,
    Baseline: pt.projected_cash_cents / 100,
    ...(scenario ? { Alternative: scenario.alternative[idx].projected_cash_cents / 100 } : {}),
  }));

  const visibleSuggestions = data.recurring_suggestions.filter(
    (s) => !dismissedMerchants.includes(`${s.merchant}|${s.category_name}`)
  );

  return (
    <div className="space-y-10">
      <section className="pb-6 border-b border-primary/15">
        <div className="flex items-center gap-3 text-[11px] text-on-surface-variant uppercase tracking-wider mb-3 font-semibold">
          <span className="text-terracotta font-bold">.01.</span>
          <span>Phase 4 · Intelligence &amp; Projections</span>
        </div>
        <h1 className="heading-display text-3xl md:text-4xl text-primary font-bold">
          Insights, Recurring Bills &amp; Forecasting
        </h1>
      </section>

      {/* Price-Creep & Hike Alerts (§4.2) */}
      {data.price_hike_alerts && data.price_hike_alerts.length > 0 && (
        <section className="bg-surface-card border border-terracotta/40 p-6 space-y-3">
          <div className="text-[10px] text-terracotta uppercase tracking-widest font-bold font-display">
            Price-Creep &amp; Hike Alerts ({data.price_hike_alerts.length})
          </div>
          <div className="space-y-2">
            {data.price_hike_alerts.map((alert) => (
              <div
                key={alert.recurring_id}
                className="flex flex-wrap items-center justify-between gap-3 border border-primary/15 p-3 bg-surface text-xs"
              >
                <div>
                  <strong className="text-primary">{alert.merchant}</strong> charged{" "}
                  <strong className="text-terracotta">{formatAudFromCents(alert.new_cents)}</strong> on{" "}
                  {alert.tx_date} (baseline was {formatAudFromCents(alert.previous_cents)},{" "}
                  <strong>+{alert.delta_pct}%</strong>).
                </div>
                <button
                  className="btn btn-primary"
                  onClick={async () => {
                    await api.updateRecurringBaseline(alert.recurring_id, alert.new_cents);
                    await load();
                  }}
                  type="button"
                >
                  Update Baseline
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Explainable Insights (§11.4) */}
      <section className="space-y-4">
        <h2 className="heading-display text-xl font-bold text-primary">
          Financial Intelligence ({data.insights.length})
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {data.insights.map((ins, idx) => (
            <div key={idx} className="bg-surface-card border border-primary/20 p-5 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] uppercase tracking-widest font-bold text-secondary">
                  {ins.severity}
                </span>
              </div>
              <h3 className="heading-display text-lg font-bold text-primary">{ins.title}</h3>
              <p className="text-xs text-primary">{ins.observation}</p>
              <div className="text-[11px] text-on-surface-variant space-y-1 pt-2 border-t border-primary/10">
                <div><strong>Evidence:</strong> {ins.evidence}</div>
                <div><strong>Why it matters:</strong> {ins.why_useful}</div>
                <div><strong>Outcome:</strong> {ins.outcome}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Your Recurring Payments (Manual + Remove) */}
      <section className="bg-surface-card border border-primary/20 p-6 md:p-8 space-y-5">
        <div>
          <h2 className="heading-display text-xl font-bold text-primary mb-1">
            Your Recurring Payments ({data.recurring.length})
          </h2>
          <p className="text-xs text-on-surface-variant">
            Add your real commitments manually or accept suggestions below. Remove any item at any time.
          </p>
        </div>

        <div className="filters" style={{ marginBottom: 0 }}>
          <input
            className="input"
            placeholder="Name / Merchant (e.g. Fauzi Rent, Spotify)"
            value={recMerchant}
            onChange={(e) => setRecMerchant(e.target.value)}
            style={{ minWidth: 220 }}
          />
          <select className="select" value={recCategory} onChange={(e) => setRecCategory(e.target.value)}>
            <option value="Rent">Rent</option>
            <option value="Utilities">Utilities</option>
            <option value="Phone">Phone</option>
            <option value="Internet">Internet</option>
            <option value="Subscription services">Subscription services</option>
            <option value="Insurance">Insurance</option>
            <option value="Tithes & Offering">Tithes &amp; Offering</option>
            <option value="Other recurring payments">Other recurring payments</option>
          </select>
          <input
            className="input"
            type="number"
            step="0.01"
            placeholder="Amount ($)"
            value={recAmount}
            onChange={(e) => setRecAmount(e.target.value)}
            style={{ width: 120 }}
          />
          <select className="select" value={recCadence} onChange={(e) => setRecCadence(e.target.value)}>
            <option value="Weekly">Weekly</option>
            <option value="Fortnightly">Fortnightly</option>
            <option value="Monthly">Monthly</option>
          </select>
          <button className="btn btn-primary" onClick={() => void handleAddManualRecurring()} type="button">
            + Add Recurring
          </button>
        </div>

        {data.recurring.length === 0 ? (
          <p className="text-xs text-on-surface-variant">
            No recurring payments saved yet. Add one above or pick from the suggestions below.
          </p>
        ) : (
          <div className="table-wrap">
            <table>
              <colgroup>
                <col style={{ width: "30%" }} />
                <col style={{ width: "22%" }} />
                <col style={{ width: "12%" }} />
                <col style={{ width: "12%" }} />
                <col style={{ width: "12%" }} />
                <col style={{ width: "12%" }} />
              </colgroup>
              <thead>
                <tr>
                  <th>Name / Merchant</th>
                  <th>Category</th>
                  <th>Cadence</th>
                  <th>Amount</th>
                  <th>Est. Monthly</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.recurring.map((r) => (
                  <tr key={r.id}>
                    <td><strong>{r.merchant}</strong></td>
                    <td><span className="badge">{r.category_name}</span></td>
                    <td>{r.cadence}</td>
                    <td>{formatAudFromCents(r.amount_cents)}</td>
                    <td><strong>{formatAudFromCents(r.estimated_monthly_cents)}</strong></td>
                    <td style={{ textAlign: "right" }}>
                      <button
                        className="btn"
                        onClick={async () => {
                          await api.deleteRecurring(r.id);
                          await load();
                        }}
                        type="button"
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Suggested Periodic Payments */}
        {visibleSuggestions.length > 0 && (
          <div className="pt-4 border-t border-primary/15 space-y-3">
            <h3 className="heading-display text-base font-bold text-primary">
              Suggested Periodic Payments ({visibleSuggestions.length})
            </h3>
            <p className="text-xs text-on-surface-variant">
              Repeated payments found in your history. Add the real commitments and ignore the rest.
            </p>
            <div className="table-wrap">
              <table>
                <colgroup>
                  <col style={{ width: "34%" }} />
                  <col style={{ width: "22%" }} />
                  <col style={{ width: "14%" }} />
                  <col style={{ width: "12%" }} />
                  <col style={{ width: "18%" }} />
                </colgroup>
                <thead>
                  <tr>
                    <th>Merchant</th>
                    <th>Category</th>
                    <th>Observed</th>
                    <th>Avg Amount</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {visibleSuggestions.slice(0, 12).map((s) => {
                    const key = `${s.merchant}|${s.category_name}`;
                    return (
                      <tr key={key}>
                        <td><strong>{s.merchant}</strong></td>
                        <td><span className="badge">{s.category_name}</span></td>
                        <td>{s.estimated_cadence} ({s.occurrences}x)</td>
                        <td>{formatAudFromCents(s.avg_amount_cents)}</td>
                        <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                          <button
                            className="btn btn-primary"
                            onClick={async () => {
                              await api.addRecurring({
                                merchant: s.merchant,
                                category_name: s.category_name,
                                amount_cents: s.avg_amount_cents,
                                cadence: s.estimated_cadence,
                              });
                              await load();
                            }}
                            style={{ marginRight: 6 }}
                            type="button"
                          >
                            + Add
                          </button>
                          <button
                            className="btn"
                            onClick={async () => {
                              await api.dismissRecurringSuggestion(s.merchant, s.category_name);
                              setDismissedMerchants((prev) => [...prev, key]);
                              await load();
                            }}
                            type="button"
                          >
                            Dismiss
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>

      {/* Cash Flow Projection & What-If Scenario */}
      <section className="bg-surface-card border border-primary/20 p-6 md:p-8 space-y-6">
        <div>
          <h2 className="heading-display text-xl font-bold text-primary mb-1">
            Cash Flow Forecast &amp; What-If Scenarios
          </h2>
          <p className="text-xs text-on-surface-variant">
            Baseline assumes {formatAudFromCents(data.monthly_income_basis_cents)}/mo income and{" "}
            {formatAudFromCents(data.monthly_expense_basis_cents)}/mo expenses. Assumptions are illustrative, not guaranteed.
          </p>
        </div>

        <div className="filters" style={{ marginBottom: 0 }}>
          <label className="text-xs">
            Extra saved / fortnight ($)
            <input
              className="input"
              type="number"
              value={extraFortnightly}
              onChange={(e) => setExtraFortnightly(e.target.value)}
              style={{ marginLeft: 8, width: 110 }}
            />
          </label>
          <label className="text-xs">
            Monthly income change ($)
            <input
              className="input"
              type="number"
              value={incomeDeltaMonthly}
              onChange={(e) => setIncomeDeltaMonthly(e.target.value)}
              style={{ marginLeft: 8, width: 110 }}
            />
          </label>
          <button className="btn btn-primary" onClick={() => void handleRunScenario()} type="button">
            Compare Scenario
          </button>
        </div>

        {scenario && (
          <div className="text-xs text-primary font-medium bg-surface-low border border-primary/15 p-3">
            5-Year Projected Difference:{" "}
            <strong>
              {scenario.five_year_difference_cents >= 0 ? "+" : ""}
              {formatAudFromCents(scenario.five_year_difference_cents)}
            </strong>
          </div>
        )}

        <div style={{ height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={forecastChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="horizon" />
              <YAxis />
              <Tooltip formatter={(val) => formatAudFromCents(Math.round(Number(val) * 100))} />
              <Legend />
              <Bar dataKey="Baseline" fill="#1B382B" />
              {scenario && <Bar dataKey="Alternative" fill="#7D9A83" />}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>
    </div>
  );
}
