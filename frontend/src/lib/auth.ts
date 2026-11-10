export const USER_TOKEN_STORAGE_KEY = "dajuice:user-token:v1";
export const USER_TOKEN_CHANGED_EVENT = "dajuice:user-token-changed";
export const AUTH_REQUIRED_EVENT = "dajuice:auth-required";
export const QUOTA_EXCEEDED_EVENT = "dajuice:quota-exceeded";

let memoryToken: string | null = null;

export interface AuthRequiredDetail {
  message?: string;
}

export interface QuotaExceededDetail {
  message: string;
  kind?: string;
  window?: string;
  retryAfter?: number;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function browserWindow(): Window | null {
  return typeof window === "undefined" ? null : window;
}

export function getUserToken(): string | null {
  try {
    const token = browserWindow()?.localStorage.getItem(USER_TOKEN_STORAGE_KEY);
    return token?.trim() || memoryToken;
  } catch {
    return memoryToken;
  }
}

export function setUserToken(token: string): void {
  const value = token.trim();
  if (!value) {
    clearUserToken();
    return;
  }
  memoryToken = value;
  try {
    browserWindow()?.localStorage.setItem(USER_TOKEN_STORAGE_KEY, value);
  } catch {
    // Private browsing can reject writes; the current tab still works in memory.
  }
  notifyTokenChanged();
}

export function clearUserToken(): void {
  memoryToken = null;
  try {
    browserWindow()?.localStorage.removeItem(USER_TOKEN_STORAGE_KEY);
  } catch {
    // Storage can be unavailable in private mode; the in-memory gate still applies.
  }
  notifyTokenChanged();
}

export function subscribeUserToken(callback: () => void): () => void {
  const win = browserWindow();
  if (!win) return () => {};

  const handleStorage = (event: StorageEvent) => {
    if (event.key === null || event.key === USER_TOKEN_STORAGE_KEY) {
      memoryToken = null;
      callback();
    }
  };

  win.addEventListener("storage", handleStorage);
  win.addEventListener(USER_TOKEN_CHANGED_EVENT, callback);
  return () => {
    win.removeEventListener("storage", handleStorage);
    win.removeEventListener(USER_TOKEN_CHANGED_EVENT, callback);
  };
}

function notifyTokenChanged(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(USER_TOKEN_CHANGED_EVENT));
}

export function authHeaders(extra?: HeadersInit): Headers {
  const headers = new Headers(extra);
  const token = getUserToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  return headers;
}

export function notifyAuthRequired(detail: AuthRequiredDetail = {}): void {
  clearUserToken();
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent<AuthRequiredDetail>(AUTH_REQUIRED_EVENT, { detail }),
  );
}

export function notifyQuotaExceeded(detail: QuotaExceededDetail): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent<QuotaExceededDetail>(QUOTA_EXCEEDED_EVENT, { detail }),
  );
}

export function errorDetailFromPayload(payload: unknown, fallback: string): string {
  if (!isRecord(payload) || !("detail" in payload)) return fallback;

  const detail = payload.detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail.trim();
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) =>
        isRecord(item) && typeof item.msg === "string" ? item.msg : "",
      )
      .filter(Boolean);
    if (messages.length > 0) return messages.join("；");
  }

  return fallback;
}

export function quotaDetailFromPayload(
  payload: unknown,
  fallback: string,
): QuotaExceededDetail {
  const message = errorDetailFromPayload(payload, fallback);
  if (!isRecord(payload)) return { message };

  return {
    message,
    kind: typeof payload.quota_kind === "string" ? payload.quota_kind : undefined,
    window: typeof payload.window === "string" ? payload.window : undefined,
    retryAfter:
      typeof payload.retry_after === "number" ? payload.retry_after : undefined,
  };
}
