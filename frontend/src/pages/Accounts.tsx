import { useEffect, useState } from "react";
import { SavingsAccount, TransferSuggestion, api, formatAudFromCents } from "../api/client";

interface Props {
  onDataChanged: () => Promise<void>;
}

export function Accounts({ onDataChanged }: Props) {
  const [tracked, setTracked] = useState<SavingsAccount[]>([]);
  const [suggestions, setSuggestions] = useState<TransferSuggestion[]>([]);
  const [names, setNames] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState<string | null>(null);

  const load = async () => {
    const [t, s] = await Promise.all([api.getSavingsAccounts(), api.getTransferSuggestions()]);
    setTracked(t);
    setSuggestions(s);
  };

  useEffect(() => {
    void load();
  }, []);

  const handleTrack = async (mask: string) => {
    const name = (names[mask] ?? "").trim();
    if (!name) {
      setMsg("Give the account a name first.");
      return;
    }
    try {
      await api.trackSavingsAccount(name, mask);
      setNames((prev) => ({ ...prev, [mask]: "" }));
      setMsg(`Now tracking "${name}".`);
      await Promise.all([load(), onDataChanged()]);
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Could not track that account.");
    }
  };

  const handleRemove = async (account: SavingsAccount) => {
    await api.deleteAccount(account.id);
    setMsg(`Stopped tracking "${account.name}".`);
    await Promise.all([load(), onDataChanged()]);
  };

  return (
    <div className="space-y-10">
      <section className="pb-6 border-b border-primary/15">
        <div className="flex items-center gap-3 text-[11px] text-on-surface-variant uppercase tracking-wider mb-3 font-semibold">
          <span className="text-terracotta font-bold">.01.</span>
          <span>Settings · Savings Tracking</span>
        </div>
        <h1 className="heading-display text-3xl md:text-4xl text-primary font-bold">
          Savings Accounts
        </h1>
        <p className="text-sm text-on-surface-variant mt-2 max-w-2xl">
          Money you transfer between your own accounts is left out of income and spending. Tell the app
          which of those accounts are savings and it will count transfers into them as money saved, and
          can feed that straight into a goal.
        </p>
      </section>

      {msg && (
        <div className="p-3 border border-secondary/40 bg-primary-light/60 text-primary text-xs font-medium">
          {msg}
        </div>
      )}

      <section className="bg-surface-card border border-primary/20 p-6 md:p-8">
        <h2 className="heading-display text-xl font-bold text-primary mb-4">
          Tracked ({tracked.length})
        </h2>
        {tracked.length === 0 ? (
          <p className="text-xs text-on-surface-variant">
            Nothing tracked yet. Pick from the detected accounts below.
          </p>
        ) : (
          <div className="table-wrap">
            <table>
              <colgroup>
                <col style={{ width: "40%" }} />
                <col style={{ width: "26%" }} />
                <col style={{ width: "14%" }} />
                <col style={{ width: "20%" }} />
              </colgroup>
              <thead>
                <tr>
                  <th>Account</th>
                  <th>Net moved in</th>
                  <th>Transfers</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {tracked.map((a) => (
                  <tr key={a.id}>
                    <td><strong>{a.name}</strong></td>
                    <td className={a.net_moved_cents >= 0 ? "amount-pos" : "amount-neg"}>
                      {formatAudFromCents(a.net_moved_cents)}
                    </td>
                    <td>{a.transfer_count}</td>
                    <td style={{ textAlign: "right" }}>
                      <button className="btn" onClick={() => void handleRemove(a)} type="button">
                        Stop tracking
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="text-[11px] text-on-surface-variant mt-3">
          &ldquo;Net moved in&rdquo; is money sent to the account minus money received back, based only on
          the transactions you have imported. It does not include interest or deposits from elsewhere.
        </p>
      </section>

      <section className="bg-surface-card border border-primary/20 p-6 md:p-8">
        <h2 className="heading-display text-xl font-bold text-primary mb-1">
          Detected transfer accounts ({suggestions.length})
        </h2>
        <p className="text-xs text-on-surface-variant mb-4">
          Accounts you transfer to or from. The last four digits are shown here only so you can tell them apart.
        </p>
        {suggestions.length === 0 ? (
          <p className="text-xs text-on-surface-variant">No untracked transfer accounts found.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <colgroup>
                <col style={{ width: "16%" }} />
                <col style={{ width: "12%" }} />
                <col style={{ width: "20%" }} />
                <col style={{ width: "32%" }} />
                <col style={{ width: "20%" }} />
              </colgroup>
              <thead>
                <tr>
                  <th>Account</th>
                  <th>Transfers</th>
                  <th>Net moved in</th>
                  <th>Name it</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {suggestions.map((s) => (
                  <tr key={s.mask}>
                    <td><strong>{s.mask}</strong></td>
                    <td>{s.count}</td>
                    <td className={s.net_moved_cents >= 0 ? "amount-pos" : "amount-neg"}>
                      {formatAudFromCents(s.net_moved_cents)}
                    </td>
                    <td>
                      <input
                        className="input"
                        placeholder="e.g. Car Saver"
                        value={names[s.mask] ?? ""}
                        onChange={(e) => setNames((prev) => ({ ...prev, [s.mask]: e.target.value }))}
                        style={{ width: "100%" }}
                      />
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <button
                        className="btn btn-primary"
                        onClick={() => void handleTrack(s.mask)}
                        type="button"
                      >
                        Track as savings
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
