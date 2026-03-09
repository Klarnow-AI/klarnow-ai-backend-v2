import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const LOCAL_API_BASE = "http://localhost:8000";
const PUBLIC_API_BASE = process.env.NEXT_PUBLIC_API_URL?.trim();
const SERVER_API_BASE = process.env.BACKEND_URL?.trim() || PUBLIC_API_BASE;

/** Backend API base URL. Client must use NEXT_PUBLIC_API_URL; server routes may use BACKEND_URL. */
export const API_BASE =
  (typeof window === "undefined" ? SERVER_API_BASE : PUBLIC_API_BASE) ||
  LOCAL_API_BASE;

export function isLocalHostname(hostname: string): boolean {
  return hostname === "localhost" || hostname === "127.0.0.1";
}

export function isLocalApiBase(value: string): boolean {
  return /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?/i.test(value);
}

export function isApiBaseMisconfiguredForBrowser(): boolean {
  if (typeof window === "undefined") return false;
  return !isLocalHostname(window.location.hostname) && isLocalApiBase(API_BASE);
}
