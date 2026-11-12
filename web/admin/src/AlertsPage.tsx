import { useCallback, useState } from "react";
import { api, when } from "./api";
import { useLoad } from "./useLoad";

const STATUSES = { open: "Open", acknowledged: "Acknowledged", resolved: "Resolved", "": "All" };

export function AlertsPage() {
  const [status, setStatus] = useState<keyof typeof STATUSES>("open");
  const fetchAlerts = useCallback(() => api.alerts(status), [status]);
  const alerts = useLoad(fetchAlerts, 30_000);
  const rules = useLoad(api.rules);
  const [error, setError] = useState<string | null>(null);
  const ruleById = new Map((rules.data?.items ?? []).map((r) => [r.id, r]));

  const acknowledge = async (id: string) => {
    setError(null);
    try { await api.acknowledge(id); alerts.reload(); } catch (e) { setError((e as Error).message); }
  };

  return (
    <main className="layout single">
      <section className="card">
        <div className="card-head">
          <h2>Alerts</h2>
          <div className="segmented">
            {(Object.keys(STATUSES) as (keyof typeof STATUSES)[]).map((s) => (
              <button key={s} className={s === status ? "on" : ""} onClick={() => setStatus(s)}>{STATUSES[s]}</button>
            ))}
          </div>
        </div>
        {(alerts.error || error) && <p className="error">{alerts.error ?? error}</p>}
        <table className="table">
          <thead>
            <tr><th>Severity</th><th>Rule</th><th>Status</th><th className="num">Move</th>
                <th className="num">Peak</th><th className="num">Price</th><th>Opened</th><th /></tr>
          </thead>
          <tbody>
            {(alerts.data?.items ?? []).map((a) => {
              const rule = ruleById.get(a.rule_id);
              return (
                <tr key={a.id} className="static">
                  <td><span className={`badge sev-${a.severity}`}>{a.severity}</span></td>
                  <td>{rule ? <><b>{rule.name}</b> <span className="muted small">{rule.provider} {rule.base}/{rule.quote}</span></> : a.rule_id}</td>
                  <td className="muted">{a.status}{a.acknowledged_by ? ` by ${a.acknowledged_by}` : ""}</td>
                  <td className={`num mono ${Number(a.change_percent) >= 0 ? "up" : "down"}`}>{signed(a.change_percent)}</td>
                  <td className="num mono">{signed(a.peak_change_percent)}</td>
                  <td className="num mono">{Number(a.current_price).toLocaleString()}</td>
                  <td className="muted small">{when(a.opened_at)}</td>
                  <td className="actions">
                    {a.status === "open" && <button className="small" onClick={() => acknowledge(a.id)}>Acknowledge</button>}
                  </td>
                </tr>
              );
            })}
            {alerts.data && alerts.data.items.length === 0 &&
              <tr className="static"><td colSpan={8} className="muted">No {status || ""} alerts.</td></tr>}
          </tbody>
        </table>
      </section>
    </main>
  );
}

const signed = (v: string) => `${Number(v) > 0 ? "+" : ""}${Number(v).toFixed(2)}%`;
