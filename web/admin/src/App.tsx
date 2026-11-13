import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { api, loadSession, saveSession, setUnauthorizedHandler } from "./api";
import type { Session } from "./api";
import { AlertsPage } from "./AlertsPage";
import { RulesPage } from "./RulesPage";
import { SyncPage } from "./SyncPage";

const TABS = { sync: "Sync", rules: "Alert rules", alerts: "Alerts" } as const;
type Tab = keyof typeof TABS;

export default function App() {
  const [session, setSession] = useState<Session | null>(loadSession);
  const [tab, setTab] = useState<Tab>("sync");

  const signOut = useCallback(() => { saveSession(null); setSession(null); }, []);
  useEffect(() => setUnauthorizedHandler(signOut), [signOut]);

  if (!session) return <Login onSignedIn={setSession} />;

  return (
    <>
      <div className="band">
        <div className="page">
          <header className="topbar">
            <div className="brand"><span className="logo">¤</span>Rates Admin</div>
            <nav>
              <span className="muted">{session.user.email}</span>
              <button className="link" onClick={signOut}>Sign out</button>
            </nav>
          </header>
          <div className="tabs" role="tablist">
            {(Object.keys(TABS) as Tab[]).map((t) => (
              <button key={t} role="tab" aria-selected={t === tab} className={t === tab ? "on" : ""}
                      onClick={() => setTab(t)}>{TABS[t]}</button>
            ))}
          </div>
        </div>
      </div>
      <div className="page lift">
        {tab === "sync" && <SyncPage />}
        {tab === "rules" && <RulesPage />}
        {tab === "alerts" && <AlertsPage />}
      </div>
    </>
  );
}

function Login({ onSignedIn }: { onSignedIn: (s: Session) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true); setError(null);
    try { onSignedIn(await api.login(email, password)); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  };

  return (
    <div className="band login-screen">
    <form className="card dialog login" onSubmit={submit}>
      <div className="dialog-head">
        <div className="logo">¤</div>
        <h2>Rates Admin</h2>
        <p className="muted small">Sign in with an admin account.</p>
      </div>
      <label>Email
        <input type="email" required autoComplete="username" value={email}
               onChange={(e) => setEmail(e.target.value)} />
      </label>
      <label>Password
        <input type="password" required autoComplete="current-password" value={password}
               onChange={(e) => setPassword(e.target.value)} />
      </label>
      {error && <p className="error">{error}</p>}
      <button type="submit" disabled={busy}>Sign in</button>
    </form>
    </div>
  );
}
