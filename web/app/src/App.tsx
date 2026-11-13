import { useCallback, useEffect, useState } from "react";
import { api, loadSession, saveSession, setUnauthorizedHandler } from "./api";
import type { Feed, Session, Subscription } from "./api";
import { AuthPanel } from "./AuthPanel";
import { FeedChart } from "./FeedChart";
import { RatesTable } from "./RatesTable";
import { Subscriptions } from "./Subscriptions";

export default function App() {
  const [session, setSession] = useState<Session | null>(loadSession);
  const [showAuth, setShowAuth] = useState(false);
  const [feeds, setFeeds] = useState<Feed[] | null>(null);
  const [feedsError, setFeedsError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);

  const signOut = useCallback(() => {
    saveSession(null);
    setSession(null);
    setSubscriptions([]);
  }, []);
  useEffect(() => setUnauthorizedHandler(signOut), [signOut]);

  useEffect(() => {
    const load = () => api.feeds().then(setFeeds, (e) => setFeedsError(String(e.message)));
    load();
    const timer = setInterval(load, 60_000);
    return () => clearInterval(timer);
  }, []);

  const reloadSubscriptions = useCallback(() => {
    if (session) api.subscriptions().then(setSubscriptions, () => setSubscriptions([]));
  }, [session]);
  useEffect(reloadSubscriptions, [reloadSubscriptions]);

  const subscribedFeedIds = new Set(subscriptions.map((s) => s.feed.id));
  const selected = feeds?.find((f) => f.id === selectedId) ?? null;

  const rising = feeds?.filter((f) => Number(f.change_percent) > 0).length;
  const falling = feeds?.filter((f) => Number(f.change_percent) < 0).length;
  const sources = feeds && new Set(feeds.map((f) => f.provider)).size;

  return (
    <>
      <div className="band">
        <div className="page">
          <header className="topbar">
            <div className="brand"><img className="logo" src="/meshcaster-mark.svg" alt="" /><span className="brand-text">Currency Rates<small>Meshcaster</small></span></div>
            <nav>
              {session ? (
                <>
                  <span className="muted">{session.user.email}</span>
                  <button className="link" onClick={signOut}>Sign out</button>
                </>
              ) : (
                <button onClick={() => setShowAuth(true)}>Sign in</button>
              )}
            </nav>
          </header>
          <div className="hero">
            <div>
              <h1>Fiat and crypto rates, in one place</h1>
              <p>Live values from central banks and exchanges, with history charts and daily email digests.</p>
            </div>
            <div className="stats">
              <Stat label="Pairs tracked" value={feeds?.length} />
              <Stat label="Sources" value={sources} />
              <Stat label="Rising" value={rising} tone="up" />
              <Stat label="Falling" value={falling} tone="down" />
            </div>
          </div>
        </div>
      </div>

      <div className="page lift">
        {showAuth && !session && (
          <AuthPanel onClose={() => setShowAuth(false)}
                     onSignedIn={(s) => { setSession(s); setShowAuth(false); }} />
        )}

        <main className="layout">
          <section className="card">
            <div className="card-head">
              <h2>Rates</h2>
              <span className="muted small">Latest synced values · updates every minute</span>
            </div>
            {feedsError && <p className="error">{feedsError}</p>}
            {feeds === null && !feedsError && <p className="muted">Loading…</p>}
            {feeds && (
              <RatesTable feeds={feeds} selectedId={selectedId} onSelect={(f) => setSelectedId(f.id)}
                          signedIn={!!session} subscribedIds={subscribedFeedIds}
                          onSubscribed={reloadSubscriptions}
                          onWantsSignIn={() => setShowAuth(true)} />
            )}
          </section>

          <aside className="side">
            {selected && <FeedChart feed={selected} onClose={() => setSelectedId(null)} />}
            {session ? (
              <Subscriptions subscriptions={subscriptions} onChanged={reloadSubscriptions} />
            ) : (
              <section className="card promo">
                <div className="promo-icon">✉</div>
                <h2>Daily emails</h2>
                <p className="muted">
                  Sign in to get any of these rates by email every day, at the hour you choose.
                </p>
                <button onClick={() => setShowAuth(true)}>Sign in or register</button>
              </section>
            )}
          </aside>
        </main>
        <p className="footer muted small">Rates are informational and may lag the market.</p>
      </div>
    </>
  );
}

function Stat({ label, value, tone }: { label: string; value: number | null | undefined; tone?: string }) {
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className={`stat-value ${tone ?? ""}`}>{value ?? "–"}</div>
    </div>
  );
}
