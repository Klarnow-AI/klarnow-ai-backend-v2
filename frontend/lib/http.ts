import type { AuthAccessToken } from "@/types/api-types";
import { API_BASE } from "./utils";

const ACCESS_TOKEN_STORAGE_KEY = "klarnow_token";
const REFRESH_PATH = "/api/v1/auth/refresh";

type ApiOptions = RequestInit & {
  base?: string;
  retryOnAuthError?: boolean;
  _retriedAfterRefresh?: boolean;
};

type ErrorResponseBody = {
  isSuccess?: unknown;
  message?: unknown;
  data?: unknown;
  detail?: unknown;
  error?: unknown;
  request_id?: unknown;
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function getPayloadData(payload: ErrorResponseBody): Record<string, unknown> {
  return isRecord(payload.data) ? payload.data : {};
}

function getRequestIdFromPayload(payload: ErrorResponseBody): unknown {
  const data = getPayloadData(payload);
  return payload.request_id ?? data.request_id;
}

function appendRequestId(message: string, requestId: unknown): string {
  if (typeof requestId !== "string" || !requestId.trim()) return message;
  return `${message} (request ${requestId})`;
}

export function getReadableFetchError(
  error: unknown,
  fallback = "Request could not reach the server. Check that the backend is running and try again.",
): string {
  if (error instanceof DOMException && error.name === "AbortError") {
    return error.message;
  }
  if (error instanceof Error) {
    const message = error.message.trim();
    if (message && message !== "Failed to fetch") return message;
  }
  return fallback;
}

export function getApiErrorMessage(
  payload: ErrorResponseBody,
  fallback: string,
): string {
  const data = getPayloadData(payload);
  const messageText =
    typeof payload.message === "string" ? payload.message.trim() : "";
  const detail = normalizeDetail(payload.detail);
  const errorName =
    typeof payload.error === "string" && payload.error.trim()
      ? payload.error.trim().replace(/_/g, " ")
      : "";
  const nestedDetail = normalizeDetail(data.detail);
  const message = messageText || detail || nestedDetail || errorName || fallback;
  return appendRequestId(message, getRequestIdFromPayload(payload));
}

export function parseApiErrorText(
  bodyText: string,
  fallback: string,
): string {
  try {
    const parsed = JSON.parse(bodyText) as ErrorResponseBody;
    return getApiErrorMessage(parsed, fallback);
  } catch {
    return bodyText.trim() || fallback;
  }
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
  let res: Response;
  try {
    res = await fetch(url, {
      ...rest,
      credentials: rest.credentials ?? "include",
      headers,
    });
  } catch (error) {
    throw new Error(getReadableFetchError(error));
  }
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
    const err = await res
      .json()
      .catch(() => ({ message: res.statusText, request_id: res.headers.get("x-request-id") } satisfies ErrorResponseBody));
    const message = getApiErrorMessage(err, String(res.status));
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}
