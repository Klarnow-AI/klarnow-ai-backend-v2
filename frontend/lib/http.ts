import type { AuthAccessToken } from "@/types/api-types";
import { API_BASE } from "./utils";

const ACCESS_TOKEN_STORAGE_KEY = "klarnow_token";
const REFRESH_PATH = "/api/v1/auth/refresh";

type ApiOptions = RequestInit & {
  base?: string;
  retryOnAuthError?: boolean;
  _retriedAfterRefresh?: boolean;
};

let refreshPromise: Promise<string | null> | null = null;

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token);
}

export function clearToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
}

export function getHeaders(includeAuth = true): HeadersInit {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const token = getToken();
  if (includeAuth && token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

export function resolveApiUrl(path: string): string {
  return path.startsWith("http") ? path : `${API_BASE}${path}`;
}

export function handleUnauthorized(): void {
  if (typeof window === "undefined") return;
  clearToken();
  window.dispatchEvent(new CustomEvent("auth:401"));
}

/** Normalize backend error detail to a string (handles array or nested shapes). */
function normalizeDetail(detail: unknown): string {
  if (detail == null) return "";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const first = detail[0];
    if (first && typeof first === "object" && "msg" in first) return String((first as { msg?: unknown }).msg ?? first);
    return detail.map(String).join("; ");
  }
  if (typeof detail === "object" && "msg" in detail) return String((detail as { msg?: unknown }).msg);
  return String(detail);
}

async function performRefreshAccessToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;

  const res = await fetch(resolveApiUrl(REFRESH_PATH), {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    clearToken();
    return null;
  }

  const data = (await res.json()) as AuthAccessToken;
  if (!data.access_token) {
    clearToken();
    return null;
  }

  setToken(data.access_token);
  return data.access_token;
}

export async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = performRefreshAccessToken().finally(() => {
    refreshPromise = null;
  });

  return refreshPromise;
}

export async function api<T>(
  path: string,
  options: ApiOptions = {}
): Promise<T> {
  const {
    base = API_BASE,
    retryOnAuthError = true,
    _retriedAfterRefresh = false,
    ...rest
  } = options;
  const url = path.startsWith("http") ? path : `${base}${path}`;
  const headers: Record<string, string> = {
    ...(getHeaders() as Record<string, string>),
    ...((rest.headers as Record<string, string>) ?? {}),
  };
  if (rest.body instanceof FormData) {
    delete headers["Content-Type"];
  }
  const res = await fetch(url, {
    ...rest,
    credentials: rest.credentials ?? "include",
    headers,
  });
  if (res.status === 401 && retryOnAuthError && !_retriedAfterRefresh) {
    const nextAccessToken = await refreshAccessToken();
    if (nextAccessToken) {
      return api<T>(path, {
        ...options,
        _retriedAfterRefresh: true,
      });
    }
    handleUnauthorized();
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const message = normalizeDetail(err.detail) || String(res.status);
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}
