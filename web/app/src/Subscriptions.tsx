import { useState } from "react";
import { api } from "./api";
import type { Subscription } from "./api";
import { pad } from "./RatesTable";

export function Subscriptions({ subscriptions, onChanged }:
  { subscriptions: Subscription[]; onChanged: () => void }) {
  return (
    <section className="card">
      <h2>My emails</h2>
      {subscriptions.length === 0 ? (
        <p className="muted">No subscriptions yet. Use “Subscribe” on a rate to get it daily.</p>
      ) : (
        <ul className="list">
          {subscriptions.map((s) => <Item key={s.id} sub={s} onChanged={onChanged} />)}
        </ul>
      )}
    </section>
  );
}

function Item({ sub, onChanged }: { sub: Subscription; onChanged: () => void }) {
  const [error, setError] = useState<string | null>(null);
  const [timezone, setTimezone] = useState(sub.timezone);

  const run = async (action: () => Promise<unknown>) => {
    setError(null);
    try { await action(); onChanged(); } catch (e) { setError((e as Error).message); }
  };

  return (
    <li className={sub.is_active ? "" : "paused"}>
      <div className="row">
        <b>{sub.feed.base}/{sub.feed.quote}</b>
        <span className="muted small">{sub.feed.provider}</span>
      </div>
      <div className="row wrap">
        <select value={sub.hour} aria-label="Hour"
                onChange={(e) => run(() => api.updateSubscription(sub.id, { hour: Number(e.target.value) }))}>
          {Array.from({ length: 24 }, (_, h) => <option key={h} value={h}>{pad(h)}:00</option>)}
        </select>
        <input className="tz" value={timezone} aria-label="Time zone"
               onChange={(e) => setTimezone(e.target.value)}
               onBlur={() => timezone !== sub.timezone &&
                 run(() => api.updateSubscription(sub.id, { timezone }))} />
        <label className="toggle">
          <input type="checkbox" checked={sub.is_active}
                 onChange={(e) => run(() => api.updateSubscription(sub.id, { is_active: e.target.checked }))} />
          {sub.is_active ? "On" : "Paused"}
        </label>
        <button className="small link danger" onClick={() => run(() => api.unsubscribe(sub.id))}>
          Remove
        </button>
      </div>
      <div className="muted small">
        {sub.last_sent_on ? `Last sent for ${sub.last_sent_on}` : "Not sent yet"}
      </div>
      {error && <div className="error small">{error}</div>}
    </li>
  );
}
