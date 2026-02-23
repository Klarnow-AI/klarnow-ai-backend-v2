import { API_BASE } from "./utils";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("klarnow_token");
}

export function getHeaders(includeAuth = true): HeadersInit {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const token = getToken();
  if (includeAuth && token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

export function handleUnauthorized(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem("klarnow_token");
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

export async function api<T>(
  path: string,
  options: RequestInit & { base?: string } = {}
): Promise<T> {
  const { base = API_BASE, ...rest } = options;
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
    headers,
  });
  if (!res.ok) {
    if (res.status === 401 && getToken()) handleUnauthorized();
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const message = normalizeDetail(err.detail) || String(res.status);
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}
