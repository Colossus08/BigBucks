import { Fragment, useState } from "react";
import { Category, Transaction, formatAudFromCents } from "../api/client";

interface Props {
  transactions: Transaction[];
  categories: Category[];
  onRecategorise?: (txId: number, categoryId: number, applyToMerchant: boolean) => Promise<void>;
  onToggleExclude?: (txId: number, excluded: boolean) => Promise<void>;
  onToggleTaxDeductible?: (txId: number, deductible: boolean, code: string | null) => Promise<void>;
  onSplit?: (txId: number, splitAmountCents: number, categoryId: number, note: string) => Promise<void>;
  onUnsplit?: (txId: number) => Promise<void>;
  compact?: boolean;
}

export function TransactionTable({
  transactions,
  categories,
  onRecategorise,
  onToggleExclude,
  onToggleTaxDeductible,
  onSplit,
  onUnsplit,
  compact = false,
}: Props) {
  const [applyAll, setApplyAll] = useState(true);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [splittingTxId, setSplittingTxId] = useState<number | null>(null);
  const [splitDollars, setSplitDollars] = useState("");
  const [splitCategoryId, setSplitCategoryId] = useState<number | "">("");
  const [splitNote, setSplitNote] = useState("");

  if (transactions.length === 0) {
    return <p style={{ color: "var(--muted)" }}>No transactions found.</p>;
  }

  const defaultUtilitiesCatId =
    categories.find((c) => c.name === "Utilities")?.id ?? categories[0]?.id ?? "";

  return (
    <div>
      {onRecategorise && (
        <label style={{ display: "inline-flex", alignItems: "center", gap: 6, marginBottom: 10, fontSize: "0.86rem" }}>
          <input
            type="checkbox"
            checked={applyAll}
            onChange={(e) => setApplyAll(e.target.checked)}
          />
          Apply category change to all transactions from the same merchant
        </label>
      )}
      <div className="table-wrap">
        <table>
          <colgroup>
            {compact ? (
              <>
                <col style={{ width: "15%" }} />
                <col style={{ width: "41%" }} />
                <col style={{ width: "26%" }} />
                <col style={{ width: "18%" }} />
              </>
            ) : (
              <>
                <col style={{ width: "12%" }} />
                <col style={{ width: "22%" }} />
                <col style={{ width: "30%" }} />
                <col style={{ width: "22%" }} />
                <col style={{ width: "14%" }} />
              </>
            )}
          </colgroup>
          <thead>
            <tr>
              <th>Date</th>
              <th>Merchant</th>
              {!compact && <th>Description</th>}
              <th>Category</th>
              <th style={{ textAlign: "right" }}>Amount</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((tx) => {
              const isSplitChild = tx.description_raw.includes("[Split:");
              return (
                <Fragment key={tx.id}>
                  <tr>
                    <td>{tx.date}</td>
                    <td>
                      <strong>{tx.merchant}</strong>
                      {tx.is_transfer && (
                        <span className="badge badge-transfer" style={{ marginLeft: 8 }}>
                          Transfer
                        </span>
                      )}
                      {tx.kind === "excluded" && (
                        <span className="badge badge-warn" style={{ marginLeft: 8 }}>
                          Excluded
                        </span>
                      )}
                      {!compact && onToggleExclude && (
                        <button
                          className="btn"
                          style={{ marginLeft: 8, padding: "1px 6px", fontSize: "0.7rem" }}
                          onClick={() => void onToggleExclude(tx.id, tx.kind !== "excluded")}
                          type="button"
                        >
                          {tx.kind === "excluded" ? "Include" : "Exclude"}
                        </button>
                      )}
                      {!compact && onToggleTaxDeductible && tx.amount_cents < 0 && (
                        <button
                          className="btn"
                          style={{ marginLeft: 6, padding: "1px 6px", fontSize: "0.7rem" }}
                          onClick={() =>
                            void onToggleTaxDeductible(
                              tx.id,
                              !tx.is_tax_deductible,
                              !tx.is_tax_deductible ? "D5" : null
                            )
                          }
                          type="button"
                        >
                          {tx.is_tax_deductible ? `Tax (${tx.deduction_category ?? "D5"})` : "+ Tax"}
                        </button>
                      )}
                      {!compact && onSplit && tx.amount_cents < -100 && !isSplitChild && (
                        <button
                          className="btn"
                          style={{ marginLeft: 6, padding: "1px 6px", fontSize: "0.7rem" }}
                          onClick={() => {
                            if (splittingTxId === tx.id) {
                              setSplittingTxId(null);
                            } else {
                              setSplittingTxId(tx.id);
                              setSplitDollars("");
                              setSplitCategoryId(defaultUtilitiesCatId);
                              setSplitNote("Bill share");
                            }
                          }}
                          type="button"
                        >
                          Split
                        </button>
                      )}
                      {!compact && onUnsplit && isSplitChild && (
                        <button
                          className="btn"
                          style={{ marginLeft: 6, padding: "1px 6px", fontSize: "0.7rem" }}
                          onClick={() => void onUnsplit(tx.id)}
                          type="button"
                        >
                          Merge
                        </button>
                      )}
                    </td>
                    {!compact && <td style={{ color: "var(--muted)" }}>{tx.description_raw}</td>}
                    <td>
                      {onRecategorise ? (
                        <select
                          className="select"
                          disabled={savingId === tx.id}
                          value={tx.category_id ?? ""}
                          onChange={async (e) => {
                            const nextCatId = Number(e.target.value);
                            if (!nextCatId) return;
                            setSavingId(tx.id);
                            try {
                              await onRecategorise(tx.id, nextCatId, applyAll);
                            } finally {
                              setSavingId(null);
                            }
                          }}
                        >
                          {categories.map((c) => (
                            <option key={c.id} value={c.id}>
                              {c.group} — {c.name}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <span className="badge">{tx.category_name}</span>
                      )}
                    </td>
                    <td
                      style={{ textAlign: "right" }}
                      className={tx.amount_cents >= 0 ? "amount-pos" : "amount-neg"}
                    >
                      {formatAudFromCents(tx.amount_cents)}
                    </td>
                  </tr>
                  {!compact && splittingTxId === tx.id && onSplit && (
                    <tr>
                      <td colSpan={5} style={{ background: "#f8fafc", padding: "10px 14px" }}>
                        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 8, fontSize: "0.82rem" }}>
                          <strong>
                            Split combined payment ({formatAudFromCents(Math.abs(tx.amount_cents))} total):
                          </strong>
                          <input
                            className="input"
                            type="number"
                            min="1"
                            step="1"
                            placeholder="Amount to split out ($)"
                            value={splitDollars}
                            onChange={(e) => setSplitDollars(e.target.value)}
                            style={{ width: 170, padding: "4px 8px" }}
                          />
                          <select
                            className="select"
                            value={splitCategoryId}
                            onChange={(e) =>
                              setSplitCategoryId(e.target.value ? Number(e.target.value) : "")
                            }
                            style={{ padding: "4px 8px" }}
                          >
                            {categories
                              .filter((c) => !c.is_income)
                              .map((c) => (
                                <option key={c.id} value={c.id}>
                                  {c.group} — {c.name}
                                </option>
                              ))}
                          </select>
                          <input
                            className="input"
                            placeholder="Note (e.g. Bills)"
                            value={splitNote}
                            onChange={(e) => setSplitNote(e.target.value)}
                            style={{ width: 150, padding: "4px 8px" }}
                          />
                          <button
                            className="btn btn-primary"
                            style={{ padding: "4px 10px" }}
                            onClick={async () => {
                              const cents = Math.round(Number(splitDollars || 0) * 100);
                              if (
                                cents <= 0 ||
                                cents >= Math.abs(tx.amount_cents) ||
                                splitCategoryId === ""
                              ) {
                                return;
                              }
                              await onSplit(tx.id, cents, Number(splitCategoryId), splitNote);
                              setSplittingTxId(null);
                            }}
                            type="button"
                          >
                            Confirm Split
                          </button>
                          <button
                            className="btn"
                            style={{ padding: "4px 10px" }}
                            onClick={() => setSplittingTxId(null)}
                            type="button"
                          >
                            Cancel
                          </button>
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
