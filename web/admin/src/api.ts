const BASE = "/api/v1";
const TOKEN_KEY = "currency-rates.admin-session";

export interface User { id: string; email: string; role: "user" | "admin"; scopes: string[] }
export interface Session { token: string; expiresAt: number; user: User }
export interface Page<T> { items: T[]; total: number; page: number; size: number }

export type SyncState = "paused" | "pending" | "backfilling" | "live" | "completed" | "failed";
export interface SyncConfiguration {
  id: string; provider: string; base: string; quote: string; interval: string;
  date_from: string; date_to: string | null; synced_until: string | null; is_active: boolean;
  options: Record<string, unknown> | null; last_run_at: string | null;
  last_status: string | null; last_error: string | null;
  progress: { state: SyncState; percent: number; days_synced: number; days_total: number;
              days_remaining: number };
}
export type Severity = "info" | "warning" | "critical";
export interface Tier { threshold_percent: string | number; severity: Severity }
export interface AlertRule {
  id: string; sync_configuration_id: string; provider: string; base: string; quote: string;
  name: string; window_minutes: number; direction: "up" | "down" | "both"; tiers: Tier[];
  is_active: boolean;
}
export interface Alert {
  id: string; rule_id: string; severity: Severity; status: "open" | "acknowledged" | "resolved";
  opened_at: string; change_percent: string; peak_change_percent: string;
  reference_price: string; current_price: string; observed_at: string;
  acknowledged_at: string | null; acknowledged_by: string | null; resolved_at: string | null;
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
  async login(email: string, password: string): Promise<Session> {
    const out = await request<{ access_token: string; expires_in: number; user: User }>(
      "POST", "/auth/login", { email, password });
    if (out.user.role !== "admin") throw new ApiError(403, "This account isn't an admin.");
    const session = { token: out.access_token, expiresAt: Date.now() + out.expires_in * 1000,
                      user: out.user };
    saveSession(session);
    return session;
  },
  syncConfigurations: () =>
    request<Page<SyncConfiguration>>("GET", "/sync-configurations?size=200"),
  createSyncConfiguration: (body: {
    provider: string; base: string; quote: string; date_from: string; date_to: string | null;
    options: Record<string, unknown> | null;
  }) => request<SyncConfiguration>("POST", "/sync-configurations", body),
  rules: () => request<Page<AlertRule>>("GET", "/alert-rules?size=200"),
  createRule: (body: Omit<AlertRule, "id" | "provider" | "base" | "quote">) =>
    request<AlertRule>("POST", "/alert-rules", body),
  updateRule: (id: string, changes: Partial<AlertRule>) =>
    request<AlertRule>("PATCH", `/alert-rules/${id}`, changes),
  deleteRule: (id: string) => request<void>("DELETE", `/alert-rules/${id}`),
  alerts: (status: string) =>
    request<Page<Alert>>("GET", `/alerts?size=200${status ? `&status=${status}` : ""}`),
  acknowledge: (id: string) => request<Alert>("POST", `/alerts/${id}/acknowledge`),
};

export const when = (iso: string | null) => (iso ? new Date(iso).toLocaleString() : "—");
