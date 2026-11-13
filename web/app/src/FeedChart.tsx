import { useEffect, useState } from "react";
import { api, formatRate } from "./api";
import type { Feed, FeedPoint } from "./api";
import { ChangePill, Pair } from "./RatesTable";

const RANGES = [7, 30, 90, 365];

export function FeedChart({ feed, onClose }: { feed: Feed; onClose: () => void }) {
  const [days, setDays] = useState(30);
  const [points, setPoints] = useState<FeedPoint[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setPoints(null); setError(null);
    api.history(feed.id, days).then(setPoints, (e) => setError(e.message));
  }, [feed.id, days]);

  const values = (points ?? []).map((p) => Number(p.value));
  const first = values[0], last = values[values.length - 1];
  const change = values.length > 1 ? String(((last - first) / first) * 100) : null;

  return (
    <section className="card">
      <div className="card-head">
        <h2><Pair base={feed.base} quote={feed.quote} /> <span className="source">{feed.provider}</span></h2>
        <button className="link" onClick={onClose} aria-label="Close">✕</button>
      </div>
      <div className="big mono">{formatRate(feed.value)}</div>
      <div className="segmented">
        {RANGES.map((d) => (
          <button key={d} className={d === days ? "on" : ""} onClick={() => setDays(d)}>
            {d < 365 ? `${d}d` : "1y"}
          </button>
        ))}
      </div>
      {error && <p className="error">{error}</p>}
      {!points && !error && <p className="muted">Loading…</p>}
      {points && points.length < 2 && <p className="muted">Not enough history yet.</p>}
      {points && points.length >= 2 && (
        <>
          <Sparkline values={values} />
          <div className="row small">
            <span className="muted">{points[0].day}</span>
            <span><ChangePill change={change} /> <span className="muted">over the period</span></span>
            <span className="muted">{points[points.length - 1].day}</span>
          </div>
          <div className="range-stats small">
            <div><span className="muted">Low</span><b className="down">{formatRate(String(Math.min(...values)))}</b></div>
            <div><span className="muted">High</span><b className="up">{formatRate(String(Math.max(...values)))}</b></div>
          </div>
        </>
      )}
    </section>
  );
}

function Sparkline({ values }: { values: number[] }) {
  const w = 320, h = 120, pad = 6;
  const min = Math.min(...values), max = Math.max(...values), span = max - min || 1;
  const xy = values.map((v, i) => [
    pad + (i / (values.length - 1)) * (w - 2 * pad),
    pad + (1 - (v - min) / span) * (h - 2 * pad),
  ]);
  const line = xy.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area = `${line} L${xy[xy.length - 1][0].toFixed(1)},${h} L${xy[0][0].toFixed(1)},${h} Z`;
  const rising = values[values.length - 1] >= values[0];
  const [lastX, lastY] = xy[xy.length - 1];
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className={`spark ${rising ? "up" : "down"}`} role="img"
         aria-label="Rate history">
      <defs>
        <linearGradient id="spark-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="currentColor" stopOpacity=".28" />
          <stop offset="1" stopColor="currentColor" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill="url(#spark-fill)" />
      <path d={line} className="spark-line" />
      <circle cx={lastX} cy={lastY} r="4" className="spark-dot" />
    </svg>
  );
}
