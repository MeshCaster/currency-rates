import { useCallback, useState } from "react";
import type { FormEvent } from "react";
import { api } from "./api";
import type { AlertRule, Severity, Tier } from "./api";
import { useLoad } from "./useLoad";

const SEVERITIES: Severity[] = ["info", "warning", "critical"];

export function RulesPage() {
  const rules = useLoad(api.rules);
  const configs = useLoad(api.syncConfigurations);
  const [error, setError] = useState<string | null>(null);
  const run = useCallback(async (action: () => Promise<unknown>) => {
    setError(null);
    try { await action(); rules.reload(); } catch (e) { setError((e as Error).message); }
  }, [rules]);

  return (
    <main className="layout single">
      <AddRule configs={configs.data?.items ?? []} onAdded={rules.reload} />
      <section className="card">
        <h2>Alert rules</h2>
        {(rules.error || error) && <p className="error">{rules.error ?? error}</p>}
        <table className="table">
          <thead>
            <tr><th>Name</th><th>Watches</th><th>Window</th><th>Direction</th><th>Tiers</th>
                <th>Active</th><th /></tr>
          </thead>
          <tbody>
            {(rules.data?.items ?? []).map((r) => (
              <tr key={r.id} className="static">
                <td><b>{r.name}</b></td>
                <td>{r.provider} {r.base}/{r.quote}</td>
                <td className="mono">{formatWindow(r.window_minutes)}</td>
                <td className="muted">{r.direction}</td>
                <td>{r.tiers.map((t) => (
                  <span key={t.severity} className={`badge sev-${t.severity}`} style={{ marginRight: 4 }}>
                    ≥{Number(t.threshold_percent)}% {t.severity}
                  </span>))}</td>
                <td>
                  <label className="toggle">
                    <input type="checkbox" checked={r.is_active}
                           onChange={(e) => run(() => api.updateRule(r.id, { is_active: e.target.checked }))} />
                    {r.is_active ? "On" : "Off"}
                  </label>
                </td>
                <td className="actions">
                  <button className="small link danger"
                          onClick={() => confirm(`Delete “${r.name}” and its alerts?`) && run(() => api.deleteRule(r.id))}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {rules.data && rules.data.items.length === 0 &&
              <tr className="static"><td colSpan={7} className="muted">No rules yet.</td></tr>}
          </tbody>
        </table>
      </section>
    </main>
  );
}

function AddRule({ configs, onAdded }: { configs: { id: string; provider: string; base: string; quote: string; interval: string }[]; onAdded: () => void }) {
  const [configId, setConfigId] = useState("");
  const [name, setName] = useState("");
  const [windowMinutes, setWindowMinutes] = useState(60);
  const [direction, setDirection] = useState<AlertRule["direction"]>("both");
  const [tiers, setTiers] = useState<Tier[]>([{ threshold_percent: 3, severity: "warning" },
                                              { threshold_percent: 5, severity: "critical" }]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const daily = configs.filter((c) => c.interval === "daily");
  const target = configId || daily[0]?.id || "";

  const setTier = (i: number, tier: Partial<Tier>) =>
    setTiers(tiers.map((t, j) => (i === j ? { ...t, ...tier } : t)));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true); setMessage(null);
    try {
      const rule = await api.createRule({ sync_configuration_id: target, name, window_minutes: windowMinutes,
                                          direction, tiers, is_active: true });
      setMessage({ ok: true, text: `Added “${rule.name}”. It starts checking once it has a sample ${formatWindow(rule.window_minutes)} old.` });
      setName("");
      onAdded();
    } catch (err) {
      setMessage({ ok: false, text: (err as Error).message });
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="card" onSubmit={submit}>
      <h2>Add alert rule</h2>
      <div className="form-grid">
        <label>Watch
          <select value={target} onChange={(e) => setConfigId(e.target.value)}>
            {daily.map((c) => <option key={c.id} value={c.id}>{c.provider} {c.base}/{c.quote}</option>)}
          </select>
        </label>
        <label>Name<input required maxLength={120} placeholder="BTC hourly swing" value={name}
                          onChange={(e) => setName(e.target.value)} /></label>
        <label>Window (minutes)<input type="number" min={1} required value={windowMinutes}
                                      onChange={(e) => setWindowMinutes(Number(e.target.value))} /></label>
        <label>Direction
          <select value={direction} onChange={(e) => setDirection(e.target.value as AlertRule["direction"])}>
            <option value="both">up or down</option><option value="up">up only</option>
            <option value="down">down only</option>
          </select>
        </label>
      </div>
      <div style={{ marginTop: ".8rem" }}>
        <div className="small muted">Tiers: a bigger move needs a more severe tier</div>
        {tiers.map((t, i) => (
          <div key={i} className="tier-row" style={{ marginTop: ".35rem" }}>
            <span className="small">≥</span>
            <input type="number" step="0.01" min="0.01" required value={t.threshold_percent}
                   onChange={(e) => setTier(i, { threshold_percent: e.target.value })} />
            <span className="small">%</span>
            <select value={t.severity} onChange={(e) => setTier(i, { severity: e.target.value as Severity })}>
              {SEVERITIES.map((s) => <option key={s}>{s}</option>)}
            </select>
            {tiers.length > 1 &&
              <button type="button" className="small link danger" onClick={() => setTiers(tiers.filter((_, j) => j !== i))}>Remove</button>}
          </div>
        ))}
        <div className="row" style={{ justifyContent: "flex-start" }}>
          {tiers.length < 3 &&
            <button type="button" className="small ghost"
                    onClick={() => setTiers([...tiers, { threshold_percent: 10, severity: "critical" }])}>Add tier</button>}
          <button type="submit" disabled={busy || !target}>Add rule</button>
        </div>
      </div>
      {message && <p className={message.ok ? "up" : "error"}>{message.text}</p>}
    </form>
  );
}

export function formatWindow(minutes: number) {
  if (minutes % 1440 === 0) return `${minutes / 1440} d`;
  if (minutes % 60 === 0) return `${minutes / 60} h`;
  return `${minutes} min`;
}
