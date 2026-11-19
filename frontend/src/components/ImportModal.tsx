import { useState } from "react";
import { Account, ImportReport, api } from "../api/client";

interface Props {
  open: boolean;
  accounts: Account[];
  onClose: () => void;
  onImported: () => Promise<void>;
}

export function ImportModal({ open, accounts, onClose, onImported }: Props) {
  const [accountId, setAccountId] = useState<number>(accounts[0]?.id ?? 1);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [report, setReport] = useState<ImportReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  if (!open) return null;

  const selectedAccountId =
    accounts.some((a) => a.id === accountId) ? accountId : (accounts[0]?.id ?? 1);

  const handleUpload = async (chosenFile?: File) => {
    const targetFile = chosenFile ?? file;
    if (!targetFile) return;
    setUploading(true);
    setError(null);
    setReport(null);
    try {
      const res = await api.importCommbankCsv(selectedAccountId, targetFile);
      setReport(res);
      await onImported();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-primary/40 backdrop-blur-xs flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-surface-card border border-primary/30 max-w-lg w-full p-8 shadow-2xl relative"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between mb-6 pb-3 border-b border-primary/15">
          <div>
            <span className="text-[10px] text-secondary uppercase tracking-widest font-bold font-display">
              CommBank NetBank Pipeline
            </span>
            <h3 className="heading-display text-2xl text-primary font-bold">
              Import Transaction CSV
            </h3>
          </div>
          <button
            className="text-on-surface-subtle hover:text-primary"
            onClick={onClose}
            type="button"
          >
            <span className="material-symbols-outlined text-lg">close</span>
          </button>
        </div>

        {accounts.length > 0 && (
          <div className="mb-4">
            <label className="block text-[10px] text-on-surface-subtle uppercase tracking-wider mb-1.5 font-semibold">
              Target Account
            </label>
            <select
              className="w-full border border-primary/25 bg-surface p-2.5 text-xs text-primary focus:outline-none focus:border-primary font-medium"
              value={selectedAccountId}
              onChange={(e) => setAccountId(Number(e.target.value))}
            >
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </div>
        )}

        <div
          className={`border-2 border-dashed p-8 text-center mb-6 transition-colors cursor-pointer ${
            dragOver
              ? "border-primary bg-primary-light/40"
              : "border-primary/25 bg-surface-low hover:border-primary"
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            const dropped = e.dataTransfer.files?.[0];
            if (dropped) {
              setFile(dropped);
              void handleUpload(dropped);
            }
          }}
        >
          <span className="material-symbols-outlined text-3xl text-primary mb-2">
            cloud_upload
          </span>
          <h4 className="font-display font-bold text-lg text-primary mb-1">
            {file ? file.name : "Drop CommBank CSV Here"}
          </h4>
          <p className="text-xs text-on-surface-variant mb-4 font-normal">
            Accepts default CBA NetBank exports (Date, Amount, Description, Balance)
          </p>
          <label className="inline-block px-4 py-2 border border-primary bg-surface text-xs text-primary font-bold cursor-pointer hover:bg-primary hover:text-white transition-colors uppercase font-display">
            Browse File System
            <input
              accept=".csv,text/csv"
              className="hidden"
              type="file"
              onChange={(e) => {
                const picked = e.target.files?.[0] ?? null;
                setFile(picked);
              }}
            />
          </label>
        </div>

        <div className="bg-surface p-3 border border-primary/10 text-[11px] text-on-surface-variant mb-6 leading-relaxed">
          <span className="text-primary font-bold block mb-1 font-display">
            SHA-256 Deduplication Guarantee:
          </span>
          Transactions are cryptographically keyed using date, cleaned merchant string,
          exact AUD value, and balance. Re-uploading does not duplicate existing rows.
        </div>

        {error && (
          <div className="mb-4 p-3 border border-terracotta/40 bg-terracotta-light text-terracotta text-xs font-medium">
            {error}
          </div>
        )}

        {report && (
          <div className="mb-4 p-3.5 border border-secondary/40 bg-primary-light/60 text-xs text-primary">
            <div className="font-display font-bold mb-1">
              Import Complete: {report.filename}
            </div>
            <div className="grid grid-cols-2 gap-1 text-[11px] text-on-surface-variant">
              <span>Total rows: {report.total_rows}</span>
              <span className="text-primary font-bold">
                Inserted: {report.inserted_rows}
              </span>
              <span>Duplicates skipped: {report.duplicate_rows}</span>
              <span>Errors: {report.error_rows}</span>
            </div>
            {report.balance_warnings && report.balance_warnings.length > 0 && (
              <div className="mt-2 pt-2 border-t border-primary/15 text-[11px] text-terracotta">
                <div className="font-bold">Balance continuity warnings:</div>
                {report.balance_warnings.map((w, idx) => (
                  <div key={idx}>{w}</div>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="flex justify-end gap-3">
          <button
            className="px-5 py-2 border border-primary/30 text-xs text-primary hover:bg-surface-low font-semibold uppercase font-display"
            onClick={onClose}
            type="button"
          >
            Close
          </button>
          <button
            className="px-5 py-2 bg-primary text-white text-xs font-bold tracking-wider hover:bg-primary-container transition-colors uppercase font-display disabled:opacity-40"
            disabled={!file || uploading}
            onClick={() => void handleUpload()}
            type="button"
          >
            {uploading ? "Importing..." : "Upload & Import"}
          </button>
        </div>
      </div>
    </div>
  );
}
