import { useState } from "react";
import type { FormEvent } from "react";
import { api, when } from "./api";
import type { SyncConfiguration } from "./api";
import { useLoad } from "./useLoad";

const PROVIDERS = ["frankfurter", "nbg", "coinbase", "binance", "kraken", "coingecko"];

export function SyncPage() {
  const { data, error, reload } = useLoad(api.syncConfigurations, 30_000);
  const items = data?.items ?? [];
  return (
    <main className="layout single">
      <AddConfiguration onAdded={reload} />
      <section className="card">
        <div className="card-head">
          <h2>Sync configurations</h2>
          <span className="muted small">{data ? `${data.total} total · refreshes every 30 s` : ""}</span>
        </div>
        {error && <p className="error">{error}</p>}
        <table className="table">
          <thead>
            <tr><th>Provider</th><th>Pair</th><th>Interval</th><th>State</th><th>Progress</th>
                <th>Synced until</th><th>Last run</th></tr>
          </thead>
          <tbody>
            {items.map((c) => <Row key={c.id} c={c} />)}
          </tbody>
        </table>
      </section>
    </main>
  );
}

function Row({ c }: { c: SyncConfiguration }) {
  const p = c.progress;
  return (
    <tr className="static">
      <td>{c.provider}{c.options ? <span className="muted small"> {JSON.stringify(c.options)}</span> : null}</td>
      <td><b>{c.base}/{c.quote}</b></td>
      <td className="muted">{c.interval}</td>
      <td><span className={`badge state-${p.state}`} title={c.last_error ?? ""}>{p.state}</span></td>
      <td>
        <div className="row" style={{ justifyContent: "flex-start", marginTop: 0 }}>
          <div className="progress" aria-label={`${p.percent}%`}><span style={{ width: `${p.percent}%` }} /></div>
          <span className="small mono">{p.percent}%</span>
          <span className="muted small">{p.days_synced}/{p.days_total} d</span>
        </div>
      </td>
      <td className="mono">{c.synced_until ?? "—"}</td>
      <td className="muted small">{when(c.last_run_at)}</td>
    </tr>
  );
}

function AddConfiguration({ onAdded }: { onAdded: () => void }) {
  const monthAgo = new Date(Date.now() - 30 * 86_400_000).toISOString().slice(0, 10);
  const [form, setForm] = useState({ provider: "nbg", base: "", quote: "", date_from: monthAgo,
                                     date_to: "", options: "" });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm({ ...form, [k]: e.target.value });

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true); setMessage(null);
    try {
      const options = form.options.trim() ? JSON.parse(form.options) : null;
      const c = await api.createSyncConfiguration({
        provider: form.provider, base: form.base, quote: form.quote, date_from: form.date_from,
        date_to: form.date_to || null, options });
      setMessage({ ok: true, text: `Added ${c.provider} ${c.base}/${c.quote}; the worker picks it up within a minute.` });
      setForm({ ...form, base: "", quote: "", options: "" });
      onAdded();
    } catch (err) {
      setMessage({ ok: false, text: err instanceof SyntaxError ? "Options must be JSON, e.g. {\"providers\": \"ECB\"}" : (err as Error).message });
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="card" onSubmit={submit}>
      <h2>Add configuration</h2>
      <div className="form-grid">
        <label>Provider
          <select value={form.provider} onChange={set("provider")}>
            {PROVIDERS.map((p) => <option key={p}>{p}</option>)}
          </select>
        </label>
        <label>Base<input required maxLength={10} placeholder="USD" value={form.base} onChange={set("base")} /></label>
        <label>Quote<input required maxLength={10} placeholder="GEL" value={form.quote} onChange={set("quote")} /></label>
        <label>From<input type="date" required value={form.date_from} onChange={set("date_from")} /></label>
        <label>To (optional)<input type="date" value={form.date_to} onChange={set("date_to")} /></label>
        <label>Options (JSON)<input placeholder='{"providers": "ECB"}' value={form.options} onChange={set("options")} /></label>
        <button type="submit" disabled={busy}>Add</button>
      </div>
      {message && <p className={message.ok ? "up" : "error"}>{message.text}</p>}
    </form>
  );
}
