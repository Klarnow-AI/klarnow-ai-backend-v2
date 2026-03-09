export type ApiErrorKind =
  | "validation"
  | "auth"
  | "permission"
  | "not_found"
  | "conflict"
  | "rate_limit"
  | "service"
  | "server";

export type AppRequestErrorKind =
  | ApiErrorKind
  | "offline"
  | "network"
  | "config"
  | "cancelled";

export type ConnectivityIssueKind = "offline" | "network" | "config";

export type ApiFieldError = {
  field: string;
  message: string;
  type?: string;
};

type AppRequestErrorOptions = {
  kind: AppRequestErrorKind;
  message: string;
  status?: number;
  code?: string | null;
  retryable?: boolean;
  requestId?: string | null;
  fieldErrors?: ApiFieldError[];
  cause?: unknown;
};

export const ERROR_MESSAGES: Record<AppRequestErrorKind, string> = {
  offline: "You're offline. Check your internet connection and try again.",
  network: "We can't reach Klarnow right now. Please try again in a moment.",
  config: "This app isn't connected to the server right now.",
  cancelled: "Request cancelled.",
  validation: "Some information needs attention. Please review and try again.",
  auth: "Authentication failed. Please try again.",
  permission: "You don't have permission to do that.",
  not_found: "We couldn't find what you were looking for.",
  conflict: "This action can't be completed right now. Please review and try again.",
  rate_limit: "You're doing that too quickly. Please wait a moment and try again.",
  service: "We're having trouble on our side. Please try again in a few moments.",
  server: "We're having trouble on our side. Please try again in a few moments.",
};

export class AppRequestError extends Error {
  kind: AppRequestErrorKind;
  status?: number;
  code?: string | null;
  retryable: boolean;
  requestId?: string | null;
  fieldErrors: ApiFieldError[];

  constructor({
    kind,
    message,
    status,
    code,
    retryable = false,
    requestId,
    fieldErrors = [],
    cause,
  }: AppRequestErrorOptions) {
    super(message);
    this.name = "AppRequestError";
    this.kind = kind;
    this.status = status;
    this.code = code ?? null;
    this.retryable = retryable;
    this.requestId = requestId ?? null;
    this.fieldErrors = fieldErrors;
    if (cause !== undefined) {
      this.cause = cause;
    }
  }
}

export function getFriendlyErrorMessage(kind: AppRequestErrorKind): string {
  return ERROR_MESSAGES[kind];
}

export function isAppRequestError(error: unknown): error is AppRequestError {
  return error instanceof AppRequestError;
}

export function isConnectivityIssueKind(
  kind: AppRequestErrorKind,
): kind is ConnectivityIssueKind {
  return kind === "offline" || kind === "network" || kind === "config";
}

export function isRequestCancelled(error: unknown): boolean {
  return (
    (error instanceof DOMException && error.name === "AbortError") ||
    (isAppRequestError(error) && error.kind === "cancelled") ||
    (error instanceof Error && error.name === "AbortError")
  );
}
