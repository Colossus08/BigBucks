import { useEffect, useState } from "react";
import {
  Account,
  Category,
  Rule,
  Transaction,
  UncategorisedMerchant,
  api,
  formatAudFromCents,
} from "../api/client";
import { TransactionTable } from "../components/TransactionTable";

interface Props {
  accounts: Account[];
  categories: Category[];
  initialCategoryFilter?: number;
  onDataChanged: () => Promise<void>;
}

export function Transactions({ accounts, categories, initialCategoryFilter, onDataChanged }: Props) {
  const [viewMode, setViewMode] = useState<"all" | "quick" | "rules">(
    initialCategoryFilter ? "quick" : "all"
  );
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [merchants, setMerchants] = useState<UncategorisedMerchant[]>([]);
  const [search, setSearch] = useState("");
  const [categoryId, setCategoryId] = useState<number | "">(initialCategoryFilter ?? "");
  const [accountId, setAccountId] = useState<number | "">("");
  const [loading, setLoading] = useState(false);

  // Quick keyword rule state
  const [rulePattern, setRulePattern] = useState("");
  const [ruleCategoryId, setRuleCategoryId] = useState<number | "">("");
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  // Multi-select bulk categorise state
  const [selectedMerchants, setSelectedMerchants] = useState<string[]>([]);
  const [bulkCategoryId, setBulkCategoryId] = useState<number | "">("");
  const [allRules, setAllRules] = useState<Rule[]>([]);
  const [ruleSearch, setRuleSearch] = useState("");
  const [ruleSourceFilter, setRuleSourceFilter] = useState<"all" | "learned" | "seed">("all");

  // Category creation state
  const [newCatName, setNewCatName] = useState("");
  const [newCatGroup, setNewCatGroup] = useState("Lifestyle");

  const loadAll = async () => {
    setLoading(true);
    try {
      const [rows, uncatMerchants, rules] = await Promise.all([
        api.getTransactions({
          q: search || undefined,
          category: categoryId === "" ? undefined : categoryId,
          account: accountId === "" ? undefined : accountId,
        }),
        api.getUncategorisedMerchants(),
        api.getRules(),
      ]);
      setTransactions(rows);
      setMerchants(uncatMerchants);
      setAllRules(rules);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadAll();
  }, [categoryId, accountId]);

  const handleAddRule = async () => {
    if (!rulePattern.trim() || ruleCategoryId === "") return;
    const res = await api.createRule(rulePattern.trim(), Number(ruleCategoryId));
    setStatusMsg(`Rule "${rulePattern.trim()}" added — categorised ${res.updated_count} transaction(s).`);
    setRulePattern("");
    await Promise.all([loadAll(), onDataChanged()]);
  };

  const handleUndoLatestRule = async () => {
    try {
      const res = await api.undoLatestRule();
      setStatusMsg(`Undid latest rule — reset ${res.updated_count} transaction(s).`);
      await Promise.all([loadAll(), onDataChanged()]);
    } catch (err) {
      setStatusMsg(err instanceof Error ? err.message : "No learned rules to undo.");
    }
  };

  const toggleMerchant = (merchant: string) => {
    setSelectedMerchants((prev) =>
      prev.includes(merchant) ? prev.filter((m) => m !== merchant) : [...prev, merchant]
    );
  };

  const handleBulkAssign = async () => {
    if (selectedMerchants.length === 0 || bulkCategoryId === "") return;
    const res = await api.bulkCategorise(selectedMerchants, Number(bulkCategoryId));
    setStatusMsg(
      `Categorised ${res.updated_count} transaction(s) across ${selectedMerchants.length} merchant(s).`
    );
    setSelectedMerchants([]);
    await Promise.all([loadAll(), onDataChanged()]);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Quick Keyword Rule Bar */}
      <div className="card">
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: 10, marginBottom: 10 }}>
          <h3 style={{ margin: 0, fontSize: "1rem" }}>Rules &amp; Categories Control Plane</h3>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button
              className="btn"
              onClick={async () => {
                const res = await api.reapplyRules();
                setStatusMsg(`Re-applied rules — categorised ${res.updated_count} transaction(s).`);
                await Promise.all([loadAll(), onDataChanged()]);
              }}
              type="button"
            >
              Re-apply Rules
            </button>
            <button className="btn" onClick={() => void handleUndoLatestRule()} type="button">
              Undo Latest Rule
            </button>
            <button
              className="btn"
              onClick={() => setViewMode("rules")}
              type="button"
            >
              View All Rules ({allRules.length})
            </button>
          </div>
        </div>
        <div className="filters" style={{ marginBottom: 0 }}>
          <input
            className="input"
            placeholder="Keyword (e.g. SHILOH, OPSM, BUNNINGS)"
            value={rulePattern}
            onChange={(e) => setRulePattern(e.target.value)}
            style={{ minWidth: 240 }}
          />
          <select
            className="select"
            value={ruleCategoryId}
            onChange={(e) => setRuleCategoryId(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">Select category...</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.group} — {c.name}
              </option>
            ))}
          </select>
          <button
            className="btn btn-primary"
            disabled={!rulePattern.trim() || ruleCategoryId === ""}
            onClick={() => void handleAddRule()}
          >
            Add &amp; Apply Rule
          </button>
        </div>
        {statusMsg && (
          <p style={{ margin: "10px 0 0", fontSize: "0.88rem", color: "var(--accent)" }}>
            {statusMsg}
          </p>
        )}
        <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--border)" }}>
          <div className="stat-label" style={{ marginBottom: 6 }}>
            Create Custom Category
          </div>
          <div className="filters" style={{ marginBottom: 0 }}>
            <input
              className="input"
              placeholder="New category name"
              value={newCatName}
              onChange={(e) => setNewCatName(e.target.value)}
            />
            <select
              className="select"
              value={newCatGroup}
              onChange={(e) => setNewCatGroup(e.target.value)}
            >
              <option value="Essential">Essential</option>
              <option value="Transport">Transport</option>
              <option value="Lifestyle">Lifestyle</option>
              <option value="Commitments">Commitments</option>
              <option value="Giving">Giving</option>
              <option value="Growth">Growth</option>
              <option value="Income">Income</option>
              <option value="Reimbursements">Reimbursements</option>
            </select>
            <button
              className="btn"
              disabled={!newCatName.trim()}
              onClick={async () => {
                await api.createCategory(
                  newCatName.trim(),
                  newCatGroup,
                  newCatGroup === "Income"
                );
                setStatusMsg(`Created category "${newCatName.trim()}".`);
                setNewCatName("");
                await onDataChanged();
              }}
              type="button"
            >
              + Add Category
            </button>
          </div>
        </div>
      </div>

      <div className="card">
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: 10, marginBottom: 14 }}>
          <div className="nav-tabs">
            <button
              className={`nav-tab ${viewMode === "quick" ? "active" : ""}`}
              onClick={() => setViewMode("quick")}
            >
              Quick Categorise by Merchant ({merchants.length})
            </button>
            <button
              className={`nav-tab ${viewMode === "all" ? "active" : ""}`}
              onClick={() => setViewMode("all")}
            >
              All Transactions ({transactions.length})
            </button>
            <button
              className={`nav-tab ${viewMode === "rules" ? "active" : ""}`}
              onClick={() => setViewMode("rules")}
            >
              Existing Rules ({allRules.length})
            </button>
          </div>
        </div>

        {viewMode === "rules" ? (
          <div>
            <div className="filters">
              <input
                className="input"
                placeholder="Search rule keyword or category..."
                value={ruleSearch}
                onChange={(e) => setRuleSearch(e.target.value)}
                style={{ minWidth: 240 }}
              />
              <select
                className="select"
                value={ruleSourceFilter}
                onChange={(e) => setRuleSourceFilter(e.target.value as "all" | "learned" | "seed")}
              >
                <option value="all">All rules ({allRules.length})</option>
                <option value="learned">
                  My learned rules ({allRules.filter((r) => r.source === "learned").length})
                </option>
                <option value="seed">
                  Default seed rules ({allRules.filter((r) => r.source === "seed").length})
                </option>
              </select>
            </div>
            <div className="table-wrap">
              <table>
                <colgroup>
                  <col style={{ width: "30%" }} />
                  <col style={{ width: "14%" }} />
                  <col style={{ width: "14%" }} />
                  <col style={{ width: "28%" }} />
                  <col style={{ width: "14%" }} />
                </colgroup>
                <thead>
                  <tr>
                    <th>Merchant / Keyword Pattern</th>
                    <th>Match Type</th>
                    <th>Source</th>
                    <th>Assigned Category</th>
                    <th style={{ textAlign: "right" }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {allRules
                    .filter((r) =>
                      ruleSourceFilter === "all" ? true : r.source === ruleSourceFilter
                    )
                    .filter((r) => {
                      if (!ruleSearch.trim()) return true;
                      const q = ruleSearch.trim().toLowerCase();
                      return (
                        r.pattern.toLowerCase().includes(q) ||
                        r.category_name.toLowerCase().includes(q)
                      );
                    })
                    .map((r) => (
                      <tr key={r.id}>
                        <td>
                          <strong>{r.pattern}</strong>
                        </td>
                        <td>{r.match_type}</td>
                        <td>
                          <span className="badge">
                            {r.source === "learned" ? "Your Rule" : "Default"}
                          </span>
                        </td>
                        <td>
                          <select
                            className="select"
                            value={r.category_id}
                            onChange={async (e) => {
                              const nextCatId = Number(e.target.value);
                              const res = await api.updateRuleCategory(r.id, nextCatId);
                              setStatusMsg(
                                `Updated rule "${r.pattern}" — re-categorised ${res.updated_count} transaction(s).`
                              );
                              await Promise.all([loadAll(), onDataChanged()]);
                            }}
                          >
                            {categories.map((c) => (
                              <option key={c.id} value={c.id}>
                                {c.group} — {c.name}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td style={{ textAlign: "right" }}>
                          <button
                            className="btn"
                            onClick={async () => {
                              const res = await api.deleteRule(r.id);
                              setStatusMsg(
                                `Deleted rule "${r.pattern}" — reset ${res.updated_count} transaction(s).`
                              );
                              await Promise.all([loadAll(), onDataChanged()]);
                            }}
                            type="button"
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : viewMode === "quick" ? (
          merchants.length === 0 ? (
            <p style={{ color: "var(--muted)" }}>All transactions are categorised!</p>
          ) : (
            <div>
              <div className="filters" style={{ alignItems: "center", background: "#f8fafc", padding: 10, borderRadius: 8 }}>
                <span style={{ fontSize: "0.88rem" }}>
                  <strong>{selectedMerchants.length}</strong> selected
                </span>
                <select
                  className="select"
                  value={bulkCategoryId}
                  onChange={(e) => setBulkCategoryId(e.target.value ? Number(e.target.value) : "")}
                >
                  <option value="">Assign selected to...</option>
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.group} — {c.name}
                    </option>
                  ))}
                </select>
                <button
                  className="btn btn-primary"
                  disabled={selectedMerchants.length === 0 || bulkCategoryId === ""}
                  onClick={() => void handleBulkAssign()}
                >
                  Apply to Selected ({selectedMerchants.length})
                </button>
              </div>
              <div className="table-wrap">
                <table>
                  <colgroup>
                    <col style={{ width: "4%" }} />
                    <col style={{ width: "22%" }} />
                    <col style={{ width: "8%" }} />
                    <col style={{ width: "12%" }} />
                    <col style={{ width: "30%" }} />
                    <col style={{ width: "24%" }} />
                  </colgroup>
                  <thead>
                    <tr>
                      <th style={{ width: 32 }}>
                        <input
                          type="checkbox"
                          checked={merchants.length > 0 && selectedMerchants.length === merchants.length}
                          onChange={(e) =>
                            setSelectedMerchants(e.target.checked ? merchants.map((m) => m.merchant) : [])
                          }
                        />
                      </th>
                      <th>Merchant</th>
                      <th>Count</th>
                      <th>Total</th>
                      <th>Sample Description</th>
                      <th>Single Assign</th>
                    </tr>
                  </thead>
                  <tbody>
                    {merchants.map((m) => (
                      <tr key={m.merchant}>
                        <td>
                          <input
                            type="checkbox"
                            checked={selectedMerchants.includes(m.merchant)}
                            onChange={() => toggleMerchant(m.merchant)}
                          />
                        </td>
                        <td><strong>{m.merchant}</strong></td>
                        <td><span className="badge">{m.count}</span></td>
                        <td className={m.total_cents >= 0 ? "amount-pos" : "amount-neg"}>
                          {formatAudFromCents(m.total_cents)}
                        </td>
                        <td style={{ color: "var(--muted)", maxWidth: 320 }}>{m.sample_description}</td>
                        <td>
                          <select
                            className="select"
                            defaultValue=""
                            onChange={async (e) => {
                              const nextCatId = Number(e.target.value);
                              if (!nextCatId) return;
                              const res = await api.updateTransaction(m.sample_transaction_id, nextCatId, true);
                              setStatusMsg(`Categorised ${res.updated_count} "${m.merchant}" transaction(s).`);
                              setSelectedMerchants((prev) => prev.filter((x) => x !== m.merchant));
                              await Promise.all([loadAll(), onDataChanged()]);
                            }}
                          >
                            <option value="" disabled>
                              Pick category...
                            </option>
                            {categories.map((c) => (
                              <option key={c.id} value={c.id}>
                                {c.group} — {c.name}
                              </option>
                            ))}
                          </select>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )
        ) : (
          <>
            <div className="filters">
              <input
                className="input"
                placeholder="Search merchant or description..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void loadAll();
                }}
              />
              <select
                className="select"
                value={accountId}
                onChange={(e) => setAccountId(e.target.value ? Number(e.target.value) : "")}
              >
                <option value="">All accounts</option>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
              <select
                className="select"
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value ? Number(e.target.value) : "")}
              >
                <option value="">All categories</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.group} — {c.name}
                  </option>
                ))}
              </select>
              <button className="btn btn-primary" onClick={() => void loadAll()}>
                Search
              </button>
            </div>

            {loading ? (
              <p style={{ color: "var(--muted)" }}>Loading transactions...</p>
            ) : (
              <TransactionTable
                transactions={transactions}
                categories={categories}
                onRecategorise={async (txId, nextCatId, applyAll) => {
                  await api.updateTransaction(txId, nextCatId, applyAll);
                  await Promise.all([loadAll(), onDataChanged()]);
                }}
                onToggleExclude={async (txId, excluded) => {
                  await api.setTransactionExcluded(txId, excluded);
                  await Promise.all([loadAll(), onDataChanged()]);
                }}
                onToggleTaxDeductible={async (txId, deductible, code) => {
                  await api.setTransactionTaxDeductible(txId, deductible, code);
                  await Promise.all([loadAll(), onDataChanged()]);
                }}
                onSplit={async (txId, splitAmountCents, catId, note) => {
                  await api.splitTransaction(txId, splitAmountCents, catId, note);
                  setStatusMsg("Split combined payment into two separate category entries.");
                  await Promise.all([loadAll(), onDataChanged()]);
                }}
                onUnsplit={async (txId) => {
                  await api.unsplitTransaction(txId);
                  setStatusMsg("Merged split entry back into the original transaction.");
                  await Promise.all([loadAll(), onDataChanged()]);
                }}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}
