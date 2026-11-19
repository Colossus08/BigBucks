import { useEffect, useState } from "react";
import {
  Goal,
  PayCyclePlan,
  SavingsAccount,
  api,
  formatAudFromCents,
} from "../api/client";

function goalFortnightlyCents(g: Goal): number {
  if (g.contribution_frequency === "weekly") return g.planned_contribution_cents * 2;
  if (g.contribution_frequency === "monthly")
    return Math.round((g.planned_contribution_cents * 12) / 26);
  return g.planned_contribution_cents;
}

export function Goals() {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [savingsAccounts, setSavingsAccounts] = useState<SavingsAccount[]>([]);
  const [payCycle, setPayCycle] = useState<PayCyclePlan | null>(null);

  const [name, setName] = useState("");
  const [targetDollars, setTargetDollars] = useState("");
  const [contribDollars, setContribDollars] = useState("100");
  const [targetDate, setTargetDate] = useState("");
  const [linkedAccountId, setLinkedAccountId] = useState<number | "">("");
  const [contribAmounts, setContribAmounts] = useState<Record<number, string>>({});
  const [editingGoalId, setEditingGoalId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [editTargetDollars, setEditTargetDollars] = useState("");
  const [editPlanDollars, setEditPlanDollars] = useState("");

  const load = async () => {
    const [g, s, p] = await Promise.all([
      api.getGoals(),
      api.getSavingsAccounts(),
      api.getPayCyclePlan(),
    ]);
    setGoals(g);
    setSavingsAccounts(s);
    setPayCycle(p);
  };

  useEffect(() => {
    void load();
  }, []);

  const handleCreate = async () => {
    if (!name.trim() || !targetDollars) return;
    await api.createGoal({
      name: name.trim(),
      category: "general",
      target_cents: Math.round(Number(targetDollars) * 100),
      extra_costs_cents: 0,
      current_cents: 0,
      target_date: targetDate || null,
      priority: goals.length + 1,
      planned_contribution_cents: Math.round(Number(contribDollars || 0) * 100),
      contribution_frequency: "fortnightly",
      linked_account_id: linkedAccountId === "" ? null : linkedAccountId,
    });
    setName("");
    setTargetDollars("");
    setTargetDate("");
    setLinkedAccountId("");
    await load();
  };

  // Fortnightly numbers connected directly to your Budget Set-Asides
  const netFnCents = payCycle?.net_fortnightly_cents ?? 0;
  const setAsidesFnCents = payCycle?.budgeted_fortnightly_cents ?? 0;
  const leftAfterSetAsidesFnCents = netFnCents - setAsidesFnCents;
  const existingGoalsFnCents = payCycle?.goal_contributions_fortnightly_cents ?? 0;
  const remainingFnCents = leftAfterSetAsidesFnCents - existingGoalsFnCents;

  const draftContribFnCents = Math.max(0, Math.round(Number(contribDollars || 0) * 100));
  const remainingAfterDraftFnCents = remainingFnCents - draftContribFnCents;
  const draftTargetCents = Math.max(0, Math.round(Number(targetDollars || 0) * 100));
  const draftFortnights =
    draftContribFnCents > 0 && draftTargetCents > 0
      ? Math.ceil(draftTargetCents / draftContribFnCents)
      : 0;

  return (
    <div className="space-y-8">
      <section className="pb-5 border-b border-primary/15">
        <h1 className="heading-display text-3xl text-primary font-bold">
          Fortnightly Savings Goals
        </h1>
        <p className="text-xs text-on-surface-variant mt-1">
          Allocate your remaining fortnightly pay across your future goals.
        </p>
      </section>

      {/* 3 Clean Fortnightly Numbers */}
      {payCycle && (
        <section className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-surface-card border border-primary/20 p-5">
            <div className="text-[10px] text-on-surface-subtle uppercase tracking-widest font-bold mb-1">
              Left After Budget Set-Asides
            </div>
            <div className="font-display text-2xl font-bold text-primary tabular-nums">
              {formatAudFromCents(leftAfterSetAsidesFnCents)}
              <span className="text-xs font-normal text-on-surface-variant"> / fn</span>
            </div>
            <div className="text-[11px] text-on-surface-variant mt-1 tabular-nums">
              {formatAudFromCents(netFnCents)} pay − {formatAudFromCents(setAsidesFnCents)} budget
              set-asides
            </div>
          </div>

          <div className="bg-surface-card border border-primary/20 p-5">
            <div className="text-[10px] text-on-surface-subtle uppercase tracking-widest font-bold mb-1">
              Allocated to Goals ({goals.length})
            </div>
            <div className="font-display text-2xl font-bold text-secondary tabular-nums">
              -{formatAudFromCents(existingGoalsFnCents)}
              <span className="text-xs font-normal text-on-surface-variant"> / fn</span>
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
              <span className="text-xs font-normal text-on-surface-variant"> / fn</span>
            </div>
          </div>
        </section>
      )}

      {/* Add New Goal */}
      <section className="bg-surface-card border border-primary/20 p-6 space-y-3">
        <h2 className="heading-display text-lg font-bold text-primary">Add New Goal</h2>
        <div className="filters" style={{ marginBottom: 0 }}>
          <input
            className="input"
            placeholder="Goal name (e.g. Mazda 3, Europe Trip)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={{ minWidth: 220 }}
          />
          <input
            className="input"
            type="number"
            placeholder="Target ($ AUD)"
            value={targetDollars}
            onChange={(e) => setTargetDollars(e.target.value)}
          />
          <input
            className="input"
            type="number"
            placeholder="$ per fortnight"
            value={contribDollars}
            onChange={(e) => setContribDollars(e.target.value)}
          />
          <input
            className="input"
            type="date"
            value={targetDate}
            onChange={(e) => setTargetDate(e.target.value)}
          />
          {savingsAccounts.length > 0 && (
            <select
              className="select"
              value={linkedAccountId}
              onChange={(e) =>
                setLinkedAccountId(e.target.value ? Number(e.target.value) : "")
              }
            >
              <option value="">No linked savings account</option>
              {savingsAccounts.map((a) => (
                <option key={a.id} value={a.id}>
                  Link: {a.name}
                </option>
              ))}
            </select>
          )}
          <button className="btn btn-primary" onClick={() => void handleCreate()} type="button">
            Create Goal
          </button>
        </div>

        {draftContribFnCents > 0 && (
          <div className="text-xs pt-1 tabular-nums">
            Allocating <strong>{formatAudFromCents(draftContribFnCents)}/fortnight</strong> leaves{" "}
            <strong
              style={{
                color: remainingAfterDraftFnCents >= 0 ? "#1B382B" : "#C86452",
              }}
            >
              {formatAudFromCents(remainingAfterDraftFnCents)} remaining this fortnight
            </strong>
            {draftFortnights > 0 ? ` · Reaches target in ~${draftFortnights} fortnights.` : "."}
          </div>
        )}
      </section>

      {/* Goal Cards */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {goals.map((g) => {
          const pct = Math.min(100, Number(g.completion_pct));
          const currentGoalFnCents = goalFortnightlyCents(g);
          const poolBeforeThisGoalFnCents = remainingFnCents + currentGoalFnCents;
          const editPlanFnCents = Math.max(0, Math.round(Number(editPlanDollars || 0) * 100));
          const poolAfterEditFnCents = poolBeforeThisGoalFnCents - editPlanFnCents;

          return (
            <div key={g.goal_id} className="bg-surface-card border border-primary/20 p-6 space-y-4">
              <div className="flex items-start justify-between gap-2">
                {editingGoalId === g.goal_id ? (
                  <div className="space-y-2 flex-1">
                    <input
                      className="input"
                      placeholder="Goal name"
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      style={{ width: "100%" }}
                    />
                    <div className="flex flex-wrap gap-2 items-center">
                      <label className="text-[11px] text-on-surface-variant">
                        Target ($):
                        <input
                          className="input ml-1"
                          type="number"
                          value={editTargetDollars}
                          onChange={(e) => setEditTargetDollars(e.target.value)}
                          style={{ width: 110 }}
                        />
                      </label>
                      <label className="text-[11px] text-on-surface-variant">
                        $/fortnight:
                        <input
                          className="input ml-1"
                          type="number"
                          value={editPlanDollars}
                          onChange={(e) => setEditPlanDollars(e.target.value)}
                          style={{ width: 100 }}
                        />
                      </label>
                    </div>
                    <div
                      className="text-[11px] tabular-nums"
                      style={{
                        color: poolAfterEditFnCents >= 0 ? "#1B382B" : "#C86452",
                        fontWeight: 600,
                      }}
                    >
                      Leaves {formatAudFromCents(poolAfterEditFnCents)} remaining this fortnight
                    </div>
                  </div>
                ) : (
                  <div>
                    <h2 className="heading-display text-2xl font-bold text-primary">{g.name}</h2>
                    <div className="text-xs text-on-surface-variant tabular-nums mt-0.5">
                      <strong>{formatAudFromCents(currentGoalFnCents)} / fortnight</strong>
                      {g.projected_completion_date
                        ? ` · Target reached by ${g.projected_completion_date}`
                        : ""}
                    </div>
                  </div>
                )}

                <div className="flex gap-1.5">
                  {editingGoalId === g.goal_id ? (
                    <>
                      <button
                        className="btn btn-primary"
                        onClick={async () => {
                          await api.updateGoal(g.goal_id, {
                            name: editName.trim() || g.name,
                            target_cents:
                              Math.round(Number(editTargetDollars || 0) * 100) || g.target_cents,
                            planned_contribution_cents: Math.round(
                              Number(editPlanDollars || 0) * 100
                            ),
                          });
                          setEditingGoalId(null);
                          await load();
                        }}
                        type="button"
                      >
                        Save
                      </button>
                      <button
                        className="btn"
                        onClick={() => setEditingGoalId(null)}
                        type="button"
                      >
                        Cancel
                      </button>
                    </>
                  ) : (
                    <button
                      className="btn"
                      onClick={() => {
                        setEditingGoalId(g.goal_id);
                        setEditName(g.name);
                        setEditTargetDollars((g.total_target_cents / 100).toFixed(0));
                        setEditPlanDollars((currentGoalFnCents / 100).toFixed(0));
                      }}
                      type="button"
                    >
                      Edit
                    </button>
                  )}
                  <button
                    className="btn"
                    onClick={async () => {
                      await api.deleteGoal(g.goal_id);
                      await load();
                    }}
                    type="button"
                  >
                    Delete
                  </button>
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1.5 tabular-nums">
                  <span>
                    <strong>{formatAudFromCents(g.current_cents)}</strong> saved
                  </span>
                  <span>
                    Target: <strong>{formatAudFromCents(g.total_target_cents)}</strong> (
                    {g.completion_pct}%)
                  </span>
                </div>
                <div style={{ height: 8, background: "#e2e8f0" }}>
                  <div style={{ width: `${pct}%`, height: "100%", background: "#1B382B" }} />
                </div>
              </div>

              {savingsAccounts.length > 0 && (
                <div className="text-xs text-on-surface-variant flex items-center justify-between gap-2 pt-1">
                  <select
                    className="select"
                    style={{ fontSize: "0.78rem", padding: "4px 8px" }}
                    value={g.linked_account_id ?? ""}
                    onChange={async (e) => {
                      const val = e.target.value;
                      if (!val) {
                        await api.updateGoal(g.goal_id, { clear_linked_account: true });
                      } else {
                        await api.updateGoal(g.goal_id, { linked_account_id: Number(val) });
                      }
                      await load();
                    }}
                  >
                    <option value="">No linked savings account</option>
                    {savingsAccounts.map((a) => (
                      <option key={a.id} value={a.id}>
                        Linked account: {a.name}
                      </option>
                    ))}
                  </select>
                  {g.linked_account_name && (
                    <span className="tabular-nums">
                      {formatAudFromCents(g.linked_moved_cents)} from transfers
                    </span>
                  )}
                </div>
              )}

              <div className="flex gap-2 pt-1">
                <input
                  className="input"
                  type="number"
                  min="1"
                  placeholder="Add manual $ saved"
                  value={contribAmounts[g.goal_id] ?? ""}
                  onChange={(e) =>
                    setContribAmounts((prev) => ({ ...prev, [g.goal_id]: e.target.value }))
                  }
                  style={{ flex: 1 }}
                />
                <button
                  className="btn btn-primary"
                  onClick={async () => {
                    const amt = Number(contribAmounts[g.goal_id] || 0);
                    if (amt <= 0) return;
                    await api.contributeGoal(g.goal_id, Math.round(amt * 100));
                    setContribAmounts((prev) => ({ ...prev, [g.goal_id]: "" }));
                    await load();
                  }}
                  type="button"
                >
                  + Add
                </button>
              </div>
            </div>
          );
        })}
      </section>
    </div>
  );
}
