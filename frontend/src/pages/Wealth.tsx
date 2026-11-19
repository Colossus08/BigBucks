import { useEffect, useState } from "react";
import { WealthDashboard, api, formatAudFromCents } from "../api/client";

const AU_EDUCATION = [
  {
    title: "ETFs & Index Funds",
    body: "Exchange-Traded Funds (ETFs) like VAS (Australian shares) or VGS (international shares) let you buy a diversified basket of companies in one ASX trade with low management fees.",
  },
  {
    title: "Dollar-Cost Averaging (DCA)",
    body: "Investing a fixed dollar amount every fortnight or month smooths out market ups and downs and builds a consistent investing habit without trying to time the market.",
  },
  {
    title: "Compound Growth & Dividends",
    body: "Reinvesting returns and ASX dividends (often with franking credits) allows your earnings to generate their own earnings over 10–30 year horizons.",
  },
  {
    title: "Superannuation (12% SG)",
    body: "Your employer contributes 12% on top of your $58,193 base salary into super. Super is long-term retirement wealth, separate from your immediately available spending cash.",
  },
];

export function Wealth() {
  const [data, setData] = useState<WealthDashboard | null>(null);
  const [symbol, setSymbol] = useState("");
  const [name, setName] = useState("");
  const [assetType, setAssetType] = useState("ETF");
  const [units, setUnits] = useState("");
  const [avgCost, setAvgCost] = useState("");
  const [currPrice, setCurrPrice] = useState("");

  const [fundName, setFundName] = useState("");
  const [superBal, setSuperBal] = useState("");
  const [personalMonthly, setPersonalMonthly] = useState("");
  const [returnPct, setReturnPct] = useState("7.0");
  const [priceEdits, setPriceEdits] = useState<Record<number, string>>({});

  const load = async () => {
    const res = await api.getWealth();
    setData(res);
    setFundName(res.super_fund_name);
    setSuperBal((res.super_balance_cents / 100).toFixed(2));
    setPersonalMonthly((res.super_personal_monthly_cents / 100).toFixed(2));
    setReturnPct((res.super_expected_return_bps / 100).toFixed(1));
  };

  useEffect(() => {
    void load();
  }, []);

  if (!data) {
    return (
      <div className="bg-surface-card border border-primary/20 p-8 text-sm text-on-surface-variant">
        Loading wealth &amp; superannuation...
      </div>
    );
  }

  return (
    <div className="space-y-10">
      <section className="pb-6 border-b border-primary/15">
        <div className="flex items-center gap-3 text-[11px] text-on-surface-variant uppercase tracking-wider mb-3 font-semibold">
          <span className="text-terracotta font-bold">.01.</span>
          <span>Phase 6 · Investments, Super &amp; Net Worth</span>
        </div>
        <h1 className="heading-display text-3xl md:text-4xl text-primary font-bold">
          Wealth &amp; Superannuation
        </h1>
      </section>

      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-surface-card border border-primary/20 p-5">
          <div className="text-[10px] text-on-surface-subtle uppercase tracking-widest font-bold mb-2">
            Total Net Worth
          </div>
          <div className="font-display text-2xl font-bold text-primary tabular-nums">
            {formatAudFromCents(data.net_worth_cents)}
          </div>
          <div className="text-[11px] text-on-surface-variant mt-1">Cash + Investments + Super</div>
        </div>
        <div className="bg-surface-card border border-primary/20 p-5">
          <div className="text-[10px] text-on-surface-subtle uppercase tracking-widest font-bold mb-2">
            Available Cash
          </div>
          <div className="font-display text-2xl font-bold text-primary tabular-nums">
            {formatAudFromCents(data.cash_cents)}
          </div>
        </div>
        <div className="bg-surface-card border border-primary/20 p-5">
          <div className="text-[10px] text-on-surface-subtle uppercase tracking-widest font-bold mb-2">
            Investments Value
          </div>
          <div className="font-display text-2xl font-bold text-secondary tabular-nums">
            {formatAudFromCents(data.investments_value_cents)}
          </div>
          <div className="text-[11px] text-on-surface-variant mt-1">
            Gain/Loss: {formatAudFromCents(data.investments_gain_loss_cents)}
          </div>
        </div>
        <div className="bg-surface-card border border-primary/20 p-5">
          <div className="text-[10px] text-on-surface-subtle uppercase tracking-widest font-bold mb-2">
            Superannuation Balance
          </div>
          <div className="font-display text-2xl font-bold text-primary tabular-nums">
            {formatAudFromCents(data.super_balance_cents)}
          </div>
          <div className="text-[11px] text-on-surface-variant mt-1">Long-term retirement wealth</div>
        </div>
      </section>

      {/* Investment Portfolio */}
      <section className="bg-surface-card border border-primary/20 p-6 md:p-8 space-y-4">
        <h2 className="heading-display text-xl font-bold text-primary">Investment Portfolio</h2>
        <div className="filters" style={{ marginBottom: 0 }}>
          <input className="input" placeholder="Symbol (e.g. VAS)" value={symbol} onChange={(e) => setSymbol(e.target.value)} style={{ width: 120 }} />
          <input className="input" placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
          <select className="select" value={assetType} onChange={(e) => setAssetType(e.target.value)}>
            <option value="ETF">ETF</option>
            <option value="Share">Share</option>
            <option value="Index Fund">Index Fund</option>
          </select>
          <input className="input" type="number" step="0.001" placeholder="Units" value={units} onChange={(e) => setUnits(e.target.value)} style={{ width: 100 }} />
          <input className="input" type="number" step="0.01" placeholder="Avg Cost ($)" value={avgCost} onChange={(e) => setAvgCost(e.target.value)} style={{ width: 120 }} />
          <input className="input" type="number" step="0.01" placeholder="Current Price ($)" value={currPrice} onChange={(e) => setCurrPrice(e.target.value)} style={{ width: 140 }} />
          <button
            className="btn btn-primary"
            onClick={async () => {
              if (!symbol || !name || !units || !avgCost || !currPrice) return;
              await api.addHolding({
                symbol,
                name,
                asset_type: assetType,
                units: Number(units),
                avg_cost_cents: Math.round(Number(avgCost) * 100),
                current_price_cents: Math.round(Number(currPrice) * 100),
              });
              setSymbol("");
              setName("");
              setUnits("");
              setAvgCost("");
              setCurrPrice("");
              await load();
            }}
            type="button"
          >
            + Add Holding
          </button>
        </div>

        {data.holdings.length > 0 && (
          <div className="table-wrap">
            <table>
              <colgroup>
                <col style={{ width: "14%" }} />
                <col style={{ width: "24%" }} />
                <col style={{ width: "10%" }} />
                <col style={{ width: "13%" }} />
                <col style={{ width: "13%" }} />
                <col style={{ width: "14%" }} />
                <col style={{ width: "12%" }} />
              </colgroup>
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Name</th>
                  <th>Units</th>
                  <th>Cost Basis</th>
                  <th>Market Value</th>
                  <th>Gain/Loss</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.holdings.map((h) => (
                  <tr key={h.holding_id}>
                    <td><strong>{h.symbol}</strong> <span className="badge">{h.asset_type}</span></td>
                    <td>{h.name}</td>
                    <td>{h.units}</td>
                    <td>{formatAudFromCents(h.cost_basis_cents)}</td>
                    <td><strong>{formatAudFromCents(h.market_value_cents)}</strong></td>
                    <td className={h.gain_loss_cents >= 0 ? "amount-pos" : "amount-neg"}>
                      {formatAudFromCents(h.gain_loss_cents)} ({h.gain_loss_pct}%)
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                        <input
                          className="input"
                          type="number"
                          step="0.01"
                          placeholder="Price $"
                          value={priceEdits[h.holding_id] ?? ""}
                          onChange={(e) =>
                            setPriceEdits((prev) => ({ ...prev, [h.holding_id]: e.target.value }))
                          }
                          style={{ width: 72, padding: "4px 6px", fontSize: "0.75rem" }}
                        />
                        <button
                          className="btn"
                          style={{ padding: "4px 6px", fontSize: "0.72rem" }}
                          onClick={async () => {
                            const nextPrice = Number(priceEdits[h.holding_id] || 0);
                            if (nextPrice <= 0) return;
                            await api.refreshHoldingPrice(h.holding_id, Math.round(nextPrice * 100));
                            setPriceEdits((prev) => ({ ...prev, [h.holding_id]: "" }));
                            await load();
                          }}
                          type="button"
                        >
                          Refresh
                        </button>
                        <button
                          className="btn"
                          style={{ padding: "4px 6px", fontSize: "0.72rem" }}
                          onClick={async () => {
                            await api.deleteHolding(h.holding_id);
                            await load();
                          }}
                          type="button"
                        >
                          ×
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Superannuation Tracker & Projection */}
      <section className="bg-surface-card border border-primary/20 p-6 md:p-8 space-y-4">
        <h2 className="heading-display text-xl font-bold text-primary">Superannuation Projection</h2>
        <div className="filters" style={{ marginBottom: 0 }}>
          <input className="input" placeholder="Fund name" value={fundName} onChange={(e) => setFundName(e.target.value)} />
          <input className="input" type="number" placeholder="Current balance ($)" value={superBal} onChange={(e) => setSuperBal(e.target.value)} />
          <input className="input" type="number" placeholder="Extra monthly ($)" value={personalMonthly} onChange={(e) => setPersonalMonthly(e.target.value)} />
          <input className="input" type="number" step="0.5" placeholder="Return % p.a." value={returnPct} onChange={(e) => setReturnPct(e.target.value)} style={{ width: 120 }} />
          <button
            className="btn btn-primary"
            onClick={async () => {
              setData(
                await api.updateSuper({
                  fund_name: fundName,
                  balance_cents: Math.round(Number(superBal || 0) * 100),
                  personal_monthly_cents: Math.round(Number(personalMonthly || 0) * 100),
                  expected_return_bps: Math.round(Number(returnPct || 7) * 100),
                })
              );
            }}
            type="button"
          >
            Update Super
          </button>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-2">
          {data.super_projections.map((p) => (
            <div key={p.years} className="border border-primary/15 p-4 bg-surface">
              <div className="text-[10px] uppercase tracking-widest text-on-surface-subtle font-bold">
                In {p.years} Years
              </div>
              <div className="font-display text-lg font-bold text-primary mt-1 tabular-nums">
                {formatAudFromCents(p.projected_balance_cents)}
              </div>
            </div>
          ))}
        </div>
        <p className="text-[11px] text-on-surface-variant">
          Assumes {returnPct}% p.a. compound return and 12% employer SG on your configured salary. Not financial advice.
        </p>
      </section>

      {/* Australian Investing Education */}
      <section className="space-y-4">
        <h2 className="heading-display text-xl font-bold text-primary">Wealth Building Foundations (AU)</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {AU_EDUCATION.map((card) => (
            <div key={card.title} className="bg-surface-card border border-primary/20 p-5">
              <h3 className="heading-display text-lg font-bold text-primary mb-2">{card.title}</h3>
              <p className="text-xs text-on-surface-variant leading-relaxed">{card.body}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
