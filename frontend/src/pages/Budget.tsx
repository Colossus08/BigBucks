import { useEffect, useState } from "react";
import {
  BudgetEval,
  Category,
  PayCyclePlan,
  api,
  formatAudFromCents,
} from "../api/client";

interface Props {
  categories: Category[];
}

function toFortnightlyCents(amountCents: number, period: string): number {
  if (period === "weekly") return amountCents * 2;
  if (period === "monthly") return Math.round((amountCents * 12) / 26);
  return amountCents;
}

export function Budget({ categories }: Props) {
  const [budgets, setBudgets] = useState<BudgetEval[]>([]);
  const [payCycle, setPayCycle] = useState<PayCyclePlan | null>(null);
  const [categoryId, setCategoryId] = useState<number | "">("");
  const [budgetName, setBudgetName] = useState("");
  const [fortnightlyDollars, setFortnightlyDollars] = useState("");
  const [editingBudgetId, setEditingBudgetId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [editDollars, setEditDollars] = useState("");
  const [editingPay, setEditingPay] = useState(false);
  const [payDollars, setPayDollars] = useState("");

  const expenseCategories = categories.filter(
    (c) => !c.is_income && c.group !== "Transfer" && c.name !== "Uncategorised"
  );

  const load = async () => {
    const [b, p] = await Promise.all([api.getBudgets(), api.getPayCyclePlan()]);
    setBudgets(b);
    setPayCycle(p);
  };

  useEffect(() => {
    void load();
  }, []);

  const handleSave = async () => {
    if (categoryId === "" || !fortnightlyDollars) return;
    const cents = Math.round(Number(fortnightlyDollars) * 100);
    if (cents <= 0) return;
    await api.upsertBudget(Number(categoryId), "fortnightly", cents, budgetName.trim());
    setFortnightlyDollars("");
    setBudgetName("");
    setCategoryId("");
    await load();
  };

  const netFnCents = payCycle?.net_fortnightly_cents ?? 0;
  const goalsFnCents = payCycle?.goal_contributions_fortnightly_cents ?? 0;

  // Total fortnightly set-asides across all saved budget items
  const setAsidesFnCents = budgets.reduce(
    (sum, b) => sum + toFortnightlyCents(b.limit_cents, b.period),
    0
  );
  const totalAllocatedFnCents = setAsidesFnCents + goalsFnCents;
  const remainingFnCents = netFnCents - totalAllocatedFnCents;

  // Live preview when typing a new set-aside
  const selectedCategory =
    categoryId !== "" ? expenseCategories.find((c) => c.id === Number(categoryId)) : undefined;
  const draftFnCents = Math.max(0, Math.round(Number(fortnightlyDollars || 0) * 100));
  const remainingAfterDraftFnCents = remainingFnCents - draftFnCents;

  return (
    <div className="space-y-8">
      <section className="pb-5 border-b border-primary/15">
        <h1 className="heading-display text-3xl text-primary font-bold">
          Fortnightly Paycheck Planner
        </h1>
        <p className="text-xs text-on-surface-variant mt-1">
          Set aside what you need from each fortnightly pay and immediately see what you have left.
        </p>
      </section>

      {/* 3 Clean Fortnightly Numbers */}
      {payCycle && (
        <section className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-surface-card border border-primary/20 p-5">
            <div className="flex items-center justify-between gap-2 mb-1">
              <div className="text-[10px] text-on-surface-subtle uppercase tracking-widest font-bold">
                Fortnightly Net Pay
              </div>
              {!editingPay && (
                <button
                  className="btn"
                  style={{ padding: "2px 8px", fontSize: "0.7rem" }}
                  onClick={() => {
                    setEditingPay(true);
                    setPayDollars((netFnCents / 100).toFixed(2).replace(/\.00$/, ""));
                  }}
                  type="button"
                >
                  Edit
                </button>
              )}
            </div>
            {editingPay ? (
              <div className="space-y-2 mt-1">
                <div className="flex items-center gap-1.5">
                  <input
                    className="input"
                    type="number"
                    min="1"
                    step="0.01"
                    placeholder="$/fortnight"
                    value={payDollars}
                    onChange={(e) => setPayDollars(e.target.value)}
                    style={{ width: 120, padding: "4px 8px", fontSize: "0.85rem" }}
                  />
                  <button
                    className="btn btn-primary"
                    style={{ padding: "4px 10px", fontSize: "0.75rem" }}
                    onClick={async () => {
                      const cents = Math.round(Number(payDollars || 0) * 100);
                      if (cents > 0) {
                        await api.updateNetPay(cents);
                        setEditingPay(false);
                        await load();
                      }
                    }}
                    type="button"
                  >
                    Save
                  </button>
                  <button
                    className="btn"
                    style={{ padding: "4px 8px", fontSize: "0.75rem" }}
                    onClick={() => setEditingPay(false)}
                    type="button"
                  >
                    Cancel
                  </button>
                </div>
                {payCycle.income_basis === "custom" && (
                  <button
                    className="text-[11px] text-on-surface-variant underline"
                    onClick={async () => {
                      await api.updateNetPay(null);
                      setEditingPay(false);
                      await load();
                    }}
                    type="button"
                  >
                    Reset to salary estimate ({formatAudFromCents(payCycle.declared_net_fortnightly_cents)})
                  </button>
                )}
              </div>
            ) : (
              <div className="font-display text-2xl font-bold text-primary tabular-nums">
                {formatAudFromCents(netFnCents)}
              </div>
            )}
          </div>

          <div className="bg-surface-card border border-primary/20 p-5">
            <div className="text-[10px] text-on-surface-subtle uppercase tracking-widest font-bold mb-1">
              Allocated This Fortnight
            </div>
            <div className="font-display text-2xl font-bold text-terracotta tabular-nums">
              -{formatAudFromCents(totalAllocatedFnCents)}
            </div>
            <div className="text-[11px] text-on-surface-variant mt-1 tabular-nums">
              {formatAudFromCents(setAsidesFnCents)} set-asides + {formatAudFromCents(goalsFnCents)}{" "}
              goals
            </div>
          </div>

          <div
            className="bg-surface-card border p-5"
            style={{
              borderColor: remainingFnCents >= 0 ? "#1B382B" : "#C86452",
            }}
          >
            <div className="text-[10px] text-on-surface-subtle uppercase tracking-widest font-bold mb-1">
              Remaining This Fortnight
            </div>
            <div
              className="font-display text-2xl font-bold tabular-nums"
              style={{
                color: remainingFnCents >= 0 ? "#1B382B" : "#C86452",
              }}
            >
              {formatAudFromCents(remainingFnCents)}
            </div>
          </div>
        </section>
      )}

      {/* Add a Fortnightly Set-Aside */}
      <section className="bg-surface-card border border-primary/20 p-6 space-y-3">
        <h2 className="heading-display text-lg font-bold text-primary">
          Add Fortnightly Set-Aside
        </h2>
        <div className="filters" style={{ marginBottom: 0 }}>
          <select
            className="select"
            value={categoryId}
            onChange={(e) => {
              const nextId = e.target.value ? Number(e.target.value) : "";
              setCategoryId(nextId);
            }}
          >
            <option value="">Select category (e.g. Rent, Groceries)...</option>
            {expenseCategories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.group} — {c.name}
              </option>
            ))}
          </select>

          <input
            className="input"
            placeholder="Budget name (optional)"
            value={budgetName}
            onChange={(e) => setBudgetName(e.target.value)}
            style={{ minWidth: 180 }}
          />

          <input
            className="input"
            type="number"
            min="1"
            step="10"
            placeholder="$ per fortnight (e.g. 390)"
            value={fortnightlyDollars}
            onChange={(e) => setFortnightlyDollars(e.target.value)}
          />

          <button className="btn btn-primary" onClick={() => void handleSave()} type="button">
            Save Set-Aside
          </button>
        </div>

        {draftFnCents > 0 && (
          <div className="text-xs pt-1 tabular-nums">
            Setting aside <strong>{formatAudFromCents(draftFnCents)}/fortnight</strong>
            {selectedCategory ? ` for ${selectedCategory.name}` : ""} leaves{" "}
            <strong
              style={{
                color: remainingAfterDraftFnCents >= 0 ? "#1B382B" : "#C86452",
              }}
            >
              {formatAudFromCents(remainingAfterDraftFnCents)} remaining this fortnight
            </strong>
            .
          </div>
        )}
      </section>

      {/* Clean List of Fortnightly Set-Asides (No "Spent" Tracking) */}
      <section className="bg-surface-card border border-primary/20 p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="heading-display text-lg font-bold text-primary">
            Your Fortnightly Set-Asides ({budgets.length})
          </h2>
          <span className="text-xs text-on-surface-variant tabular-nums">
            Total: <strong>{formatAudFromCents(setAsidesFnCents)} / fortnight</strong>
          </span>
        </div>

        {budgets.length === 0 ? (
          <p className="text-xs text-on-surface-variant">
            No fortnightly set-asides added yet. Add an item above (like $390 for Rent) to subtract
            it from your fortnightly pay.
          </p>
        ) : (
          <div className="divide-y divide-primary/10 border border-primary/15 bg-surface">
            {budgets.map((b) => {
              const fnCents = toFortnightlyCents(b.limit_cents, b.period);
              const isEditing = editingBudgetId === b.budget_id;
              const displayName = b.name?.trim() || b.category_name;
              return (
                <div
                  key={b.budget_id}
                  className="p-4 flex flex-wrap items-center justify-between gap-3"
                >
                  <div>
                    <strong className="text-sm text-primary">{displayName}</strong>{" "}
                    {displayName !== b.category_name && (
                      <span className="text-xs text-on-surface-variant">({b.category_name}) </span>
                    )}
                    <span className="badge">{b.category_group}</span>
                  </div>

                  <div className="flex items-center gap-3 text-sm tabular-nums">
                    {isEditing ? (
                      <>
                        <input
                          className="input"
                          placeholder="Budget name"
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          style={{ width: 170, padding: "4px 8px" }}
                        />
                        <input
                          className="input"
                          type="number"
                          min="1"
                          value={editDollars}
                          onChange={(e) => setEditDollars(e.target.value)}
                          style={{ width: 100, padding: "4px 8px" }}
                        />
                        <button
                          className="btn btn-primary"
                          onClick={async () => {
                            const cents = Math.round(Number(editDollars || 0) * 100);
                            if (cents > 0) {
                              await api.updateBudget(b.budget_id, {
                                name: editName.trim() || b.category_name,
                                period: "fortnightly",
                                limit_cents: cents,
                              });
                              setEditingBudgetId(null);
                              await load();
                            }
                          }}
                          type="button"
                        >
                          Save
                        </button>
                        <button
                          className="btn"
                          onClick={() => setEditingBudgetId(null)}
                          type="button"
                        >
                          Cancel
                        </button>
                      </>
                    ) : (
                      <>
                        <strong className="text-primary">
                          {formatAudFromCents(fnCents)} / fortnight
                        </strong>
                        <button
                          className="btn"
                          onClick={() => {
                            setEditingBudgetId(b.budget_id);
                            setEditName(displayName);
                            setEditDollars(String(Math.round(fnCents / 100)));
                          }}
                          type="button"
                        >
                          Edit
                        </button>
                        <button
                          className="btn"
                          onClick={async () => {
                            await api.deleteBudget(b.budget_id);
                            await load();
                          }}
                          type="button"
                        >
                          Remove
                        </button>
                      </>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
