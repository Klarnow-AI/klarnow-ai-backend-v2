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
    throw new Error(err.detail || String(res.status));
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}
