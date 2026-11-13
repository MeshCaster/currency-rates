import { useState } from "react";
import type { FormEvent } from "react";
import { api } from "./api";
import type { Session } from "./api";

export function AuthPanel({ onSignedIn, onClose }:
  { onSignedIn: (s: Session) => void; onClose: () => void }) {
  const [mode, setMode] = useState<"signin" | "register">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      if (mode === "register") await api.register(email, password);
      onSignedIn(await api.login(email, password));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="overlay" onClick={onClose}>
      <form className="card dialog" onClick={(e) => e.stopPropagation()} onSubmit={submit}>
        <div className="dialog-head">
          <div className="logo">¤</div>
          <h2>{mode === "signin" ? "Welcome back" : "Create your account"}</h2>
          <p className="muted small">Get your favourite rates by email every day.</p>
        </div>
        <div className="segmented wide">
          <button type="button" className={mode === "signin" ? "on" : ""}
                  onClick={() => setMode("signin")}>Sign in</button>
          <button type="button" className={mode === "register" ? "on" : ""}
                  onClick={() => setMode("register")}>Register</button>
        </div>
        <label>Email
          <input type="email" required autoComplete="email" value={email}
                 onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label>Password
          <input type="password" required minLength={mode === "register" ? 8 : 1}
                 autoComplete={mode === "register" ? "new-password" : "current-password"}
                 value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        {mode === "register" && <p className="muted small">At least 8 characters.</p>}
        {error && <p className="error">{error}</p>}
        <div className="row">
          <button type="button" className="link" onClick={onClose}>Cancel</button>
          <button type="submit" disabled={busy}>
            {mode === "signin" ? "Sign in" : "Create account"}
          </button>
        </div>
      </form>
    </div>
  );
}
