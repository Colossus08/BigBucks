import { useEffect, useState } from "react";
import {
  IncomeEstimate,
  SalaryReconciliation,
  TaxDeductionsDashboard,
  api,
  formatAudFromCents,
  formatAudFromDollars,
} from "../api/client";

interface Props {
  incomeEstimate: IncomeEstimate | null;
  onDataChanged: () => Promise<void>;
}

export function TaxAndEngine({ incomeEstimate, onDataChanged }: Props) {
  const [recon, setRecon] = useState<SalaryReconciliation | null>(null);
  const [taxData, setTaxData] = useState<TaxDeductionsDashboard | null>(null);
  const [wfhDate, setWfhDate] = useState("");
  const [wfhHours, setWfhHours] = useState("8");
  const [wfhNote, setWfhNote] = useState("");

  // Editable income profile
  const [employer, setEmployer] = useState("");
  const [grossSalary, setGrossSalary] = useState("");
  const [payFreq, setPayFreq] = useState("fortnightly");

  const load = async () => {
    const [r, t] = await Promise.all([
      api.getSalaryReconciliation(),
      api.getTaxDeductions(),
    ]);
    setRecon(r);
    setTaxData(t);
    setEmployer(r.employer_name);
    setPayFreq(r.pay_frequency);
  };

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    if (incomeEstimate) {
      setGrossSalary(String(incomeEstimate.gross_annual));
    }
  }, [incomeEstimate]);

  const handleAddWfh = async () => {
    if (!wfhDate || !wfhHours) return;
    await api.addWfhLog(wfhDate, Number(wfhHours), wfhNote);
    setWfhDate("");
    setWfhNote("");
    await Promise.all([load(), onDataChanged()]);
  };

  return (
    <div className="space-y-10">
      <section className="pb-6 border-b border-primary/15 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 text-[11px] text-on-surface-variant uppercase tracking-wider mb-3 font-semibold">
            <span className="text-terracotta font-bold">.01.</span>
            <span>ATO FY {taxData?.financial_year ?? "2026–27"}</span>
            <span className="text-primary/30">/</span>
            <span className="text-secondary font-bold">Salary Reconciliation &amp; WFH Ledger</span>
          </div>
          <h1 className="heading-display text-3xl md:text-4xl text-primary font-bold">
            Taxation, Salary Reconciliation &amp; WFH
          </h1>
        </div>
        <a
          className="btn btn-primary"
          href={api.exportTaxDeductionsUrl}
          style={{ textDecoration: "none" }}
        >
          Export EOFY Tax CSV
        </a>
      </section>

      {/* Real-Time Salary Reconciliation (§3.1) */}
      {recon && incomeEstimate && (
        <section className="bg-surface-card border border-primary/20 p-6 md:p-8 space-y-4">
          <div className="flex items-start justify-between pb-4 border-b border-primary/10">
            <div>
              <div className="text-[10px] text-warm-gold uppercase tracking-widest mb-1 font-bold font-display">
                .02. Real-Time Salary Reconciliation
              </div>
              <h2 className="heading-display text-2xl font-bold text-primary">
                {recon.employer_name} · Declared vs. Bank Direct Credits
              </h2>
            </div>
            <span className="px-2.5 py-1 border border-primary/20 bg-primary-light text-primary text-[11px] font-bold uppercase font-display">
              {recon.pay_frequency}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 border border-primary/15 bg-surface">
              <div className="text-[10px] text-on-surface-subtle uppercase font-semibold mb-1">
                Declared Net / Pay
              </div>
              <div className="font-display text-2xl font-bold text-primary tabular-nums">
                {formatAudFromCents(recon.expected_net_period_cents)}
              </div>
              <div className="text-[11px] text-on-surface-variant mt-1">
                Gross {formatAudFromDollars(incomeEstimate.gross_annual)}/yr
              </div>
            </div>

            <div className="p-4 border border-primary/15 bg-surface">
              <div className="text-[10px] text-on-surface-subtle uppercase font-semibold mb-1">
                Actual Avg Salary Credit
              </div>
              <div className="font-display text-2xl font-bold text-secondary tabular-nums">
                {formatAudFromCents(recon.actual_avg_period_cents)}
              </div>
              <div className="text-[11px] text-on-surface-variant mt-1">
                Across {recon.salary_deposit_count} bank credit(s)
              </div>
            </div>

            <div className="p-4 border border-primary/15 bg-surface">
              <div className="text-[10px] text-on-surface-subtle uppercase font-semibold mb-1">
                YTD Salary Credits
              </div>
              <div className="font-display text-2xl font-bold text-primary tabular-nums">
                {formatAudFromCents(recon.ytd_actual_salary_cents)}
              </div>
              <div className="text-[11px] text-on-surface-variant mt-1">
                Super: {formatAudFromDollars(incomeEstimate.super_period)}/pay
              </div>
            </div>

            <div className="p-4 border border-primary/15 bg-surface">
              <div className="text-[10px] text-on-surface-subtle uppercase font-semibold mb-1">
                Variance / Pay
              </div>
              <div className="font-display text-2xl font-bold text-primary tabular-nums">
                {recon.variance_cents >= 0 ? "+" : ""}
                {formatAudFromCents(recon.variance_cents)}
              </div>
              <div className="text-[11px] text-on-surface-variant mt-1">
                Tax + Medicare: -{formatAudFromDollars(incomeEstimate.total_tax_period)}/pay
              </div>
            </div>
          </div>

          <div className="filters pt-2 border-t border-primary/10" style={{ marginBottom: 0 }}>
            <input
              className="input"
              placeholder="Employer"
              value={employer}
              onChange={(e) => setEmployer(e.target.value)}
            />
            <input
              className="input"
              type="number"
              step="100"
              placeholder="Gross annual salary ($)"
              value={grossSalary}
              onChange={(e) => setGrossSalary(e.target.value)}
            />
            <select
              className="select"
              value={payFreq}
              onChange={(e) => setPayFreq(e.target.value)}
            >
              <option value="weekly">Weekly</option>
              <option value="fortnightly">Fortnightly</option>
              <option value="monthly">Monthly</option>
            </select>
            <button
              className="btn btn-primary"
              onClick={async () => {
                const cents = Math.round(Number(grossSalary || 0) * 100);
                if (cents <= 0) return;
                await api.updateIncomeProfile({
                  employer_name: employer,
                  gross_annual_cents: cents,
                  pay_frequency: payFreq,
                  super_rate_bps: 1200,
                });
                await Promise.all([load(), onDataChanged()]);
              }}
              type="button"
            >
              Update Salary Profile
            </button>
          </div>
        </section>
      )}

      {/* ATO Tax Deduction & WFH Ledger (§4.4) */}
      {taxData && (
        <section className="bg-surface-card border border-primary/20 p-6 md:p-8 space-y-6">
          <div>
            <div className="text-[10px] text-terracotta uppercase tracking-widest mb-1 font-bold font-display">
              .03. EOFY Tax Deduction &amp; WFH Ledger
            </div>
            <h2 className="heading-display text-2xl font-bold text-primary">
              Claimable Summary ({taxData.financial_year})
            </h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-4 border border-primary/15 bg-surface">
              <div className="text-[10px] text-on-surface-subtle uppercase font-semibold mb-1">
                WFH Fixed-Rate (67c/hr)
              </div>
              <div className="font-display text-2xl font-bold text-primary tabular-nums">
                {formatAudFromCents(taxData.wfh_deduction_cents)}
              </div>
              <div className="text-[11px] text-on-surface-variant mt-1">
                {taxData.wfh_hours_total} hours logged
              </div>
            </div>
            <div className="p-4 border border-primary/15 bg-surface">
              <div className="text-[10px] text-on-surface-subtle uppercase font-semibold mb-1">
                Tagged Work Expenses (D1–D5)
              </div>
              <div className="font-display text-2xl font-bold text-secondary tabular-nums">
                {formatAudFromCents(taxData.expense_deduction_cents)}
              </div>
              <div className="text-[11px] text-on-surface-variant mt-1">
                {taxData.deductible_transactions.length} tagged transaction(s)
              </div>
            </div>
            <div className="p-4 border border-primary/15 bg-surface">
              <div className="text-[10px] text-on-surface-subtle uppercase font-semibold mb-1">
                Total EOFY Claimable
              </div>
              <div className="font-display text-2xl font-bold text-primary tabular-nums">
                {formatAudFromCents(taxData.total_claimable_cents)}
              </div>
            </div>
          </div>

          <div className="filters" style={{ marginBottom: 0 }}>
            <input
              className="input"
              type="date"
              value={wfhDate}
              onChange={(e) => setWfhDate(e.target.value)}
            />
            <input
              className="input"
              type="number"
              step="0.5"
              min="0.5"
              max="24"
              placeholder="Hours"
              value={wfhHours}
              onChange={(e) => setWfhHours(e.target.value)}
              style={{ width: 100 }}
            />
            <input
              className="input"
              placeholder="Note (optional)"
              value={wfhNote}
              onChange={(e) => setWfhNote(e.target.value)}
            />
            <button className="btn btn-primary" onClick={() => void handleAddWfh()} type="button">
              + Log WFH Hours
            </button>
          </div>

          {taxData.wfh_logs.length > 0 && (
            <div className="table-wrap">
              <table>
                <colgroup>
                  <col style={{ width: "22%" }} />
                  <col style={{ width: "16%" }} />
                  <col style={{ width: "44%" }} />
                  <col style={{ width: "18%" }} />
                </colgroup>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Hours</th>
                    <th>Note</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {taxData.wfh_logs.map((w) => (
                    <tr key={w.id}>
                      <td>{w.work_date}</td>
                      <td><strong>{w.hours}h</strong></td>
                      <td>{w.note || "Work from home"}</td>
                      <td style={{ textAlign: "right" }}>
                        <button
                          className="btn"
                          onClick={async () => {
                            await api.deleteWfhLog(w.id);
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
        </section>
      )}
    </div>
  );
}
