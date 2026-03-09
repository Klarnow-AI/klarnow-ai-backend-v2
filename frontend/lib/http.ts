import {
  AppRequestError,
  type ApiErrorKind,
  type ApiFieldError,
  getFriendlyErrorMessage,
  isAppRequestError,
  isConnectivityIssueKind,
  isRequestCancelled,
} from "@/lib/request-errors";
import { clearConnectivityIssue, reportConnectivityIssue } from "@/store/useConnectivityStore";
import type { AuthAccessToken } from "@/types/api-types";
import { API_BASE, isApiBaseMisconfiguredForBrowser } from "./utils";

const ACCESS_TOKEN_STORAGE_KEY = "klarnow_token";
const REFRESH_PATH = "/api/v1/auth/refresh";
const SESSION_EXPIRED_MESSAGE = "Your session expired. Sign in again to continue.";

type ApiOptions = RequestInit & {
  base?: string;
  retryOnAuthError?: boolean;
  _retriedAfterRefresh?: boolean;
  authToken?: string | null;
  includeAuth?: boolean;
  defaultContentType?: boolean;
};

type ErrorResponseBody = {
  isSuccess?: unknown;
  message?: unknown;
  data?: unknown;
  detail?: unknown;
  error?: unknown;
  request_id?: unknown;
};

type ErrorResponseMeta = {
  category?: unknown;
  code?: unknown;
  retryable?: unknown;
};

const API_ERROR_KINDS: ApiErrorKind[] = [
  "validation",
  "auth",
  "permission",
  "not_found",
  "conflict",
  "rate_limit",
  "service",
  "server",
];

let refreshPromise: Promise<string | null> | null = null;

export { AppRequestError } from "@/lib/request-errors";
export {
  getFriendlyErrorMessage,
  isAppRequestError,
  isRequestCancelled,
} from "@/lib/request-errors";

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

function resolveAuthToken(authToken?: string | null): string | null {
  if (authToken !== undefined) return authToken;
  return getToken();
}

export function getHeaders(
  includeAuth = true,
  authToken?: string | null,
  defaultContentType = true,
): HeadersInit {
  const headers: Record<string, string> = {};
  if (defaultContentType) {
    headers["Content-Type"] = "application/json";
  }
  const token = resolveAuthToken(authToken);
  if (includeAuth && token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export function resolveApiUrl(path: string): string {
  return path.startsWith("http") ? path : `${API_BASE}${path}`;
}

export function handleUnauthorized(): void {
  if (typeof window === "undefined") return;
  clearToken();
  window.dispatchEvent(
    new CustomEvent("auth:401", {
      detail: { message: SESSION_EXPIRED_MESSAGE },
    }),
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isApiErrorKind(value: string): value is ApiErrorKind {
  return API_ERROR_KINDS.includes(value as ApiErrorKind);
}

function normalizeDetail(detail: unknown): string {
  if (detail == null) return "";
  if (typeof detail === "string") return detail.trim();
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (isRecord(item) && typeof item.msg === "string") {
          return item.msg.trim();
        }
        return String(item).trim();
      })
      .filter(Boolean)
      .join("; ");
  }
  if (isRecord(detail) && typeof detail.msg === "string") {
    return detail.msg.trim();
  }
  return String(detail).trim();
}

function getPayloadData(payload: ErrorResponseBody): Record<string, unknown> {
  return isRecord(payload.data) ? payload.data : {};
}

function getPayloadMessage(payload: ErrorResponseBody): string {
  const data = getPayloadData(payload);
  const topLevelMessage =
    typeof payload.message === "string" ? payload.message.trim() : "";
  const detail = normalizeDetail(payload.detail);
  const nestedDetail = normalizeDetail(data.detail);
  const legacyError =
    typeof payload.error === "string" ? payload.error.trim().replace(/_/g, " ") : "";
  return topLevelMessage || detail || nestedDetail || legacyError;
}

function getPayloadErrorMeta(payload: ErrorResponseBody): ErrorResponseMeta {
  return isRecord(payload.error) ? (payload.error as ErrorResponseMeta) : {};
}

function getRequestIdFromPayload(payload: ErrorResponseBody): string | null {
  const data = getPayloadData(payload);
  const requestId = payload.request_id ?? data.request_id;
  if (typeof requestId !== "string") return null;
  const trimmed = requestId.trim();
  return trimmed || null;
}

function getFieldErrorsFromPayload(payload: ErrorResponseBody): ApiFieldError[] {
  const data = getPayloadData(payload);
  const rawErrors = data.errors;
  if (!Array.isArray(rawErrors)) return [];
  return rawErrors
    .filter(isRecord)
    .map((item) => ({
      field: typeof item.field === "string" ? item.field : "request",
      message: typeof item.message === "string" ? item.message : "Invalid value",
      ...(typeof item.type === "string" ? { type: item.type } : {}),
    }));
}

function mapStatusToKind(status?: number): ApiErrorKind {
  if (status === 401) return "auth";
  if (status === 403) return "permission";
  if (status === 404) return "not_found";
  if (status === 409 || status === 422) return "conflict";
  if (status === 429) return "rate_limit";
  if (status === 502 || status === 503 || status === 504) return "service";
  if (typeof status === "number" && status >= 500) return "server";
  return "validation";
}

function defaultErrorCode(kind: ApiErrorKind, status?: number): string {
  switch (kind) {
    case "validation":
      return status === 422 ? "precondition_failed" : "validation_error";
    case "auth":
      return "unauthorized";
    case "permission":
      return "forbidden";
    case "not_found":
      return "not_found";
    case "conflict":
      return status === 422 ? "precondition_failed" : "conflict";
    case "rate_limit":
      return "rate_limited";
    case "service":
      return status === 502 ? "upstream_failure" : "service_unavailable";
    case "server":
      return "server_error";
    default:
      return "request_error";
  }
}

function defaultRetryable(kind: ApiErrorKind): boolean {
  return kind === "rate_limit" || kind === "service" || kind === "server";
}

function shouldUseRawApiMessage(kind: ApiErrorKind): boolean {
  return (
    kind === "validation" ||
    kind === "conflict" ||
    kind === "not_found" ||
    kind === "auth" ||
    kind === "permission" ||
    kind === "rate_limit"
  );
}

function getFallbackMessage(fallback: string): string {
  const trimmed = fallback.trim();
  if (!trimmed || /^\d{3}$/.test(trimmed)) return "";
  return trimmed;
}

function createRequestError(error: AppRequestError): AppRequestError {
  if (typeof window !== "undefined" && isConnectivityIssueKind(error.kind)) {
    reportConnectivityIssue(error.kind, error.message);
  }
  return error;
}

function createClientRequestError(
  kind: "offline" | "network" | "config" | "cancelled",
  options?: Partial<Pick<AppRequestError, "message" | "retryable" | "code">> & {
    cause?: unknown;
  },
): AppRequestError {
  return createRequestError(
    new AppRequestError({
      kind,
      message: options?.message ?? getFriendlyErrorMessage(kind),
      code: options?.code ?? kind,
      retryable: options?.retryable ?? kind !== "cancelled",
      cause: options?.cause,
    }),
  );
}

export function getApiError(
  payload: ErrorResponseBody,
  fallback: string,
  options: {
    status?: number;
    requestId?: string | null;
  } = {},
): AppRequestError {
  const errorMeta = getPayloadErrorMeta(payload);
  const explicitCategory =
    typeof errorMeta.category === "string" ? errorMeta.category.trim() : "";
  const kind =
    explicitCategory && isApiErrorKind(explicitCategory)
      ? explicitCategory
      : mapStatusToKind(options.status);
  const rawMessage = getPayloadMessage(payload);
  const fallbackMessage = getFallbackMessage(fallback);
  const requestId = getRequestIdFromPayload(payload) ?? options.requestId ?? null;
  const code =
    typeof errorMeta.code === "string" && errorMeta.code.trim()
      ? errorMeta.code.trim()
      : defaultErrorCode(kind, options.status);
  const retryable =
    typeof errorMeta.retryable === "boolean"
      ? errorMeta.retryable
      : defaultRetryable(kind);
  const message =
    shouldUseRawApiMessage(kind) && rawMessage
      ? rawMessage
      : shouldUseRawApiMessage(kind) && fallbackMessage
        ? fallbackMessage
        : getFriendlyErrorMessage(kind);

  return createRequestError(
    new AppRequestError({
      kind,
      message,
      status: options.status,
      code,
      retryable,
      requestId,
      fieldErrors: getFieldErrorsFromPayload(payload),
    }),
  );
}

export function getApiErrorMessage(
  payload: ErrorResponseBody,
  fallback: string,
  options?: {
    status?: number;
    requestId?: string | null;
  },
): string {
  return getApiError(payload, fallback, options).message;
}

export function parseApiErrorText(
  bodyText: string,
  fallback: string,
  options: {
    status?: number;
    requestId?: string | null;
  } = {},
): AppRequestError {
  const trimmed = bodyText.trim();
  if (!trimmed) {
    return createRequestError(
      new AppRequestError({
        kind: mapStatusToKind(options.status),
        message: getFriendlyErrorMessage(mapStatusToKind(options.status)),
        status: options.status,
        code: defaultErrorCode(mapStatusToKind(options.status), options.status),
        retryable: defaultRetryable(mapStatusToKind(options.status)),
        requestId: options.requestId ?? null,
      }),
    );
  }
  try {
    return getApiError(JSON.parse(trimmed) as ErrorResponseBody, fallback, options);
  } catch {
    return getApiError(
      { message: trimmed },
      fallback,
      options,
    );
  }
}

export async function getApiErrorFromResponse(
  res: Response,
  fallback: string,
): Promise<AppRequestError> {
  const requestId = res.headers.get("x-request-id");
  const bodyText = await res.text().catch(() => "");
  return parseApiErrorText(bodyText, fallback, {
    status: res.status,
    requestId,
  });
}

function normalizeThrownFetchError(error: unknown): AppRequestError {
  if (isAppRequestError(error)) return error;
  if (isRequestCancelled(error)) {
    const message =
      error instanceof Error && error.message.trim()
        ? error.message
        : getFriendlyErrorMessage("cancelled");
    return createClientRequestError("cancelled", {
      message,
      retryable: false,
      code: "cancelled",
      cause: error,
    });
  }
  if (typeof window !== "undefined") {
    if (isApiBaseMisconfiguredForBrowser()) {
      return createClientRequestError("config", { cause: error });
    }
    if (!window.navigator.onLine) {
      return createClientRequestError("offline", { cause: error });
    }
  }
  return createClientRequestError("network", { cause: error });
}

function buildHeaders(
  headersInit: HeadersInit | undefined,
  options: {
    includeAuth: boolean;
    authToken?: string | null;
    defaultContentType: boolean;
    body?: BodyInit | null;
  },
): Headers {
  const { includeAuth, authToken, defaultContentType, body } = options;
  const headers = new Headers(headersInit);
  if (defaultContentType && !(body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const token = resolveAuthToken(authToken);
  if (includeAuth && token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  return headers;
}

export async function fetchApiResponse(
  path: string,
  options: ApiOptions = {},
): Promise<Response> {
  const {
    base = API_BASE,
    retryOnAuthError = true,
    _retriedAfterRefresh = false,
    authToken,
    includeAuth = true,
    defaultContentType = true,
    ...rest
  } = options;

  if (typeof window !== "undefined" && isApiBaseMisconfiguredForBrowser()) {
    throw createClientRequestError("config");
  }

  const url = path.startsWith("http") ? path : `${base}${path}`;
  const headers = buildHeaders(rest.headers, {
    includeAuth,
    authToken,
    defaultContentType,
    body: rest.body,
  });

  let res: Response;
  try {
    res = await fetch(url, {
      ...rest,
      credentials: rest.credentials ?? "include",
      headers,
    });
  } catch (error) {
    throw normalizeThrownFetchError(error);
  }

  if (typeof window !== "undefined") {
    clearConnectivityIssue();
  }

  if (res.status === 401 && retryOnAuthError && !_retriedAfterRefresh) {
    const nextAccessToken = await refreshAccessToken();
    if (nextAccessToken) {
      return fetchApiResponse(path, {
        ...options,
        _retriedAfterRefresh: true,
      });
    }
    handleUnauthorized();
  }

  return res;
}

export function getReadableFetchError(
  error: unknown,
  fallback = getFriendlyErrorMessage("network"),
): string {
  if (isAppRequestError(error)) return error.message;
  if (isRequestCancelled(error) && error instanceof Error && error.message.trim()) {
    return error.message;
  }
  return fallback;
}

async function performRefreshAccessToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;

  const res = await fetchApiResponse(REFRESH_PATH, {
    method: "POST",
    includeAuth: false,
    retryOnAuthError: false,
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
  options: ApiOptions = {},
): Promise<T> {
  const res = await fetchApiResponse(path, options);
  if (!res.ok) {
    throw await getApiErrorFromResponse(res, "Request failed.");
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}
