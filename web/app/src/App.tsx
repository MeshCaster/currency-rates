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

  return (
    <div className="page">
      <header className="topbar">
        <div className="brand">Currency Rates</div>
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
            <section className="card">
              <h2>Daily emails</h2>
              <p className="muted">
                Sign in to get any of these rates by email every day, at the hour you choose.
              </p>
              <button onClick={() => setShowAuth(true)}>Sign in or register</button>
            </section>
          )}
        </aside>
      </main>
    </div>
  );
}
