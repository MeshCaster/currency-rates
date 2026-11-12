const BASE = "/api/v1";
const TOKEN_KEY = "currency-rates.session";

export type Role = "user" | "admin";
export interface User { id: string; email: string; role: Role; scopes: string[] }
export interface Session { token: string; expiresAt: number; user: User }

export interface Feed {
  id: string; provider: string; base: string; quote: string;
  value: string | null; as_of: string | null; previous_value: string | null;
  change_percent: string | null;
}
export interface FeedPoint { day: string; value: string }
export interface Subscription {
  id: string; feed: { id: string; provider: string; base: string; quote: string };
  hour: number; timezone: string; is_active: boolean; last_sent_on: string | null;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

let onUnauthorized: () => void = () => {};
export function setUnauthorizedHandler(handler: () => void) { onUnauthorized = handler; }

export function loadSession(): Session | null {
  try {
    const raw = localStorage.getItem(TOKEN_KEY);
    const session = raw ? (JSON.parse(raw) as Session) : null;
    return session && session.expiresAt > Date.now() ? session : null;
  } catch {
    return null;
  }
}

export function saveSession(session: Session | null) {
  try {
    if (session) localStorage.setItem(TOKEN_KEY, JSON.stringify(session));
    else localStorage.removeItem(TOKEN_KEY);
  } catch {  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const session = loadSession();
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (session) headers.Authorization = `Bearer ${session.token}`;
  const response = await fetch(BASE + path, {
    method, headers, body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (response.status === 401 && session) onUnauthorized();
  if (!response.ok) throw new ApiError(response.status, await problemMessage(response));
  return (response.status === 204 ? undefined : await response.json()) as T;
}

async function problemMessage(response: Response): Promise<string> {
  try {
    const problem = await response.json();
    const first = Array.isArray(problem.errors) ? problem.errors[0] : undefined;
    if (first?.msg) return `${(first.loc ?? []).slice(-1)[0] ?? "request"}: ${first.msg}`;
    return problem.detail ?? problem.title ?? response.statusText;
  } catch {
    return response.statusText || `HTTP ${response.status}`;
  }
}

export const api = {
  register: (email: string, password: string) =>
    request<User>("POST", "/auth/register", { email, password }),
  async login(email: string, password: string): Promise<Session> {
    const out = await request<{ access_token: string; expires_in: number; user: User }>(
      "POST", "/auth/login", { email, password });
    const session = { token: out.access_token, expiresAt: Date.now() + out.expires_in * 1000,
                      user: out.user };
    saveSession(session);
    return session;
  },
  feeds: () => request<Feed[]>("GET", "/feeds"),
  history: (feedId: string, days: number) =>
    request<FeedPoint[]>("GET", `/feeds/${feedId}/history?days=${days}`),
  subscriptions: () => request<Subscription[]>("GET", "/me/subscriptions"),
  subscribe: (feed_id: string, hour: number, timezone: string) =>
    request<Subscription>("POST", "/me/subscriptions", { feed_id, hour, timezone }),
  updateSubscription: (id: string, changes: Partial<Pick<Subscription, "hour" | "timezone" | "is_active">>) =>
    request<Subscription>("PATCH", `/me/subscriptions/${id}`, changes),
  unsubscribe: (id: string) => request<void>("DELETE", `/me/subscriptions/${id}`),
};

export function formatRate(value: string | null): string {
  if (value === null) return "—";
  const n = Number(value);
  return n.toLocaleString(undefined, { maximumFractionDigits: Math.abs(n) >= 1000 ? 2 : 4,
                                       minimumFractionDigits: Math.abs(n) >= 1000 ? 2 : 4 });
}

export function formatChange(value: string | null): string {
  if (value === null) return "—";
  const n = Number(value);
  return `${n > 0 ? "▲" : n < 0 ? "▼" : "="} ${Math.abs(n).toFixed(2)}%`;
}

export const browserTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
