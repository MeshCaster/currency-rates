import { useState } from "react";
import { api, browserTimeZone, formatChange, formatRate } from "./api";
import type { Feed } from "./api";

interface Props {
  feeds: Feed[];
  selectedId: string | null;
  onSelect: (feed: Feed) => void;
  signedIn: boolean;
  subscribedIds: Set<string>;
  onSubscribed: () => void;
  onWantsSignIn: () => void;
}

export function RatesTable(props: Props) {
  const [filter, setFilter] = useState("");
  const needle = filter.trim().toUpperCase();
  const rows = props.feeds.filter((f) =>
    !needle || `${f.base}/${f.quote} ${f.provider}`.toUpperCase().includes(needle));

  return (
    <>
      <input className="search" placeholder="Filter, e.g. GEL or btc" value={filter}
             onChange={(e) => setFilter(e.target.value)} />
      <table className="table">
        <thead>
          <tr><th>Pair</th><th>Source</th><th className="num">Rate</th>
              <th className="num">Change</th><th>As of</th><th /></tr>
        </thead>
        <tbody>
          {rows.map((f) => (
            <tr key={f.id} className={f.id === props.selectedId ? "selected" : ""}
                onClick={() => props.onSelect(f)}>
              <td><Pair base={f.base} quote={f.quote} /></td>
              <td><span className="source">{f.provider}</span></td>
              <td className="num mono">{formatRate(f.value)}</td>
              <td className="num"><ChangePill change={f.change_percent} /></td>
              <td className="muted small">{f.as_of ? new Date(f.as_of).toLocaleDateString() : "—"}</td>
              <td className="actions" onClick={(e) => e.stopPropagation()}>
                <SubscribeButton feed={f} {...props} />
              </td>
            </tr>
          ))}
          {rows.length === 0 && <tr><td colSpan={6} className="muted">No rates match.</td></tr>}
        </tbody>
      </table>
    </>
  );
}

function SubscribeButton({ feed, signedIn, subscribedIds, onSubscribed, onWantsSignIn }:
  { feed: Feed } & Props) {
  const [open, setOpen] = useState(false);
  const [hour, setHour] = useState(9);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (subscribedIds.has(feed.id)) return <span className="badge ok">Subscribed</span>;
  if (!signedIn) return <button className="small ghost" onClick={onWantsSignIn}>Subscribe</button>;
  if (!open) return <button className="small ghost" onClick={() => setOpen(true)}>Subscribe</button>;

  const submit = async () => {
    setBusy(true); setError(null);
    try {
      await api.subscribe(feed.id, hour, browserTimeZone);
      setOpen(false);
      onSubscribed();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <span className="inline-form">
      <select value={hour} onChange={(e) => setHour(Number(e.target.value))} aria-label="Hour">
        {Array.from({ length: 24 }, (_, h) => <option key={h} value={h}>{pad(h)}:00</option>)}
      </select>
      <button className="small" disabled={busy} onClick={submit}>Daily</button>
      <button className="small link" onClick={() => setOpen(false)}>Cancel</button>
      {error && <span className="error small">{error}</span>}
    </span>
  );
}

export function changeClass(change: string | null) {
  if (change === null) return "muted";
  const n = Number(change);
  return n > 0 ? "up" : n < 0 ? "down" : "muted";
}

export const pad = (h: number) => String(h).padStart(2, "0");

export function Pair({ base, quote }: { base: string; quote: string }) {
  return (
    <span className="pair">
      <span className="coins"><Coin code={base} /><Coin code={quote} /></span>
      <b>{base}/{quote}</b>
    </span>
  );
}

function Coin({ code }: { code: string }) {
  let hash = 0;
  for (const ch of code) hash = (hash * 47 + ch.charCodeAt(0) * 13) % 360;
  const bg = `linear-gradient(135deg, hsl(${hash} 75% 55%), hsl(${(hash + 40) % 360} 70% 45%))`;
  return <span className="coin" style={{ background: bg }} aria-hidden>{code.slice(0, 3)}</span>;
}

export function ChangePill({ change }: { change: string | null }) {
  return <span className={`pill ${changeClass(change)}`}>{formatChange(change)}</span>;
}
