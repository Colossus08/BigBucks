import { FormEvent, useState } from "react";
import { api } from "../api/client";

interface Props {
  onSuccess: () => Promise<void> | void;
}

export function Login({ onSuccess }: Props) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError("Enter both username and password.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await api.login(username.trim(), password);
      await onSuccess();
    } catch {
      setError("Invalid username or password.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface text-on-surface flex items-center justify-center px-6 py-12">
      <div className="w-full max-w-md bg-surface-card border border-primary/20 p-8 md:p-10">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-8 h-8 border border-primary flex items-center justify-center text-primary">
            <span className="font-display font-bold text-xs">AT</span>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-widest text-on-surface-subtle font-bold">
              Personal Finance Manager
            </div>
            <h1 className="heading-display text-2xl font-bold text-primary">Sign In</h1>
          </div>
        </div>

        <form className="space-y-5" onSubmit={(e) => void handleSubmit(e)}>
          <div>
            <label
              className="block text-[11px] uppercase tracking-wider font-bold text-on-surface-variant mb-1.5"
              htmlFor="login-username"
            >
              Username
            </label>
            <input
              id="login-username"
              type="text"
              autoComplete="username"
              className="input w-full"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Username"
              autoFocus
            />
          </div>

          <div>
            <label
              className="block text-[11px] uppercase tracking-wider font-bold text-on-surface-variant mb-1.5"
              htmlFor="login-password"
            >
              Password
            </label>
            <div className="relative">
              <input
                id="login-password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                className="input w-full pr-16"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
              />
              <button
                type="button"
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[11px] font-bold uppercase tracking-wider text-on-surface-variant hover:text-primary"
                onClick={() => setShowPassword((v) => !v)}
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </div>

          {error && (
            <div className="border border-terracotta/40 bg-terracotta/10 text-terracotta px-3.5 py-2.5 text-xs font-medium">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-primary text-white py-2.5 px-4 text-xs font-bold uppercase tracking-wider font-display hover:opacity-95 disabled:opacity-60 transition-opacity"
          >
            {submitting ? "Signing in..." : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  );
}
